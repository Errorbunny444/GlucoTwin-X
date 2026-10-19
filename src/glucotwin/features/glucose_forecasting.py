import pandas as pd
import numpy as np

def build_patient_features(twin_id, df_cgm, df_meals, df_activity, df_static, is_online=False, online_timestamp=None):
    """
    Build forecasting features for a single digital twin.
    Prevents cross-patient leakage and future leakage.
    If is_online=True, only builds features for a single online_timestamp without looking for future targets.
    """
    if df_cgm is None or len(df_cgm) == 0:
        return pd.DataFrame()
        
    df_cgm = df_cgm.sort_values('timestamp').reset_index(drop=True)
    
    if is_online:
        t_grid = [pd.to_datetime(online_timestamp)]
    else:
        start_time = df_cgm['timestamp'].min()
        end_time = df_cgm['timestamp'].max()
        start_grid = start_time.floor('5min')
        end_grid = end_time.ceil('5min')
        t_grid = pd.date_range(start_grid, end_grid, freq='5min')
        
    df_grid = pd.DataFrame({'prediction_timestamp': t_grid})
    df_grid['digital_twin_id'] = twin_id
    
    # Pre-process CGM
    cgm_ts = df_cgm[['timestamp', 'glucose']].copy()
    cgm_ts.set_index('timestamp', inplace=True)
    cgm_ts = cgm_ts.dropna(subset=['glucose'])
    cgm_ts = cgm_ts[~cgm_ts.index.duplicated(keep='first')]
    cgm_for_merge = cgm_ts.reset_index()
    
    if not is_online:
        # --- CGM TARGETS ---
        cgm_rev = cgm_ts.copy()
        cgm_rev = cgm_rev.sort_index(ascending=True)
        ref_time = cgm_rev.index.max() + pd.Timedelta(days=1)
        cgm_rev.index = ref_time - cgm_rev.index
        cgm_rev = cgm_rev.sort_index(ascending=True)
        
        future_120m_max = cgm_rev['glucose'].rolling('120min', closed='left').max()
        future_120m_max.index = ref_time - future_120m_max.index
        future_120m_max = future_120m_max.sort_index()
        cgm_ts['future_120m_max'] = future_120m_max
        cgm_ts['target_high_glucose_120m'] = (future_120m_max >= 180).astype(float)
        
        cgm_for_merge = cgm_ts.reset_index()
        
        # Target 120m
        df_target_lookup = df_grid[['prediction_timestamp']].copy()
        df_target_lookup['target_time'] = df_target_lookup['prediction_timestamp'] + pd.Timedelta(minutes=120)
        
        merged_targets = pd.merge_asof(
            df_target_lookup.sort_values('target_time'),
            cgm_for_merge.sort_values('timestamp'),
            left_on='target_time',
            right_on='timestamp',
            direction='nearest',
            tolerance=pd.Timedelta(minutes=10)
        )
        df_grid['target_glucose_120m'] = merged_targets.set_index('prediction_timestamp').loc[df_grid['prediction_timestamp'], 'glucose'].values
        
        # Other Targets
        merged_future_stats = pd.merge_asof(
            df_grid[['prediction_timestamp']].sort_values('prediction_timestamp'),
            cgm_for_merge[['timestamp', 'future_120m_max', 'target_high_glucose_120m']].sort_values('timestamp'),
            left_on='prediction_timestamp',
            right_on='timestamp',
            direction='backward',
            tolerance=pd.Timedelta(minutes=5)
        )
        df_grid['target_peak_glucose_next_120m'] = merged_future_stats.set_index('prediction_timestamp').loc[df_grid['prediction_timestamp'], 'future_120m_max'].values
        df_grid['target_high_glucose_120m'] = merged_future_stats.set_index('prediction_timestamp').loc[df_grid['prediction_timestamp'], 'target_high_glucose_120m'].values
    
    # --- CGM FEATURES (Backward looking) ---
    lags = [0, 5, 15, 30, 60, 120]
    for lag in lags:
        lookup = df_grid[['prediction_timestamp']].copy()
        lookup['lookup_time'] = lookup['prediction_timestamp'] - pd.Timedelta(minutes=lag)
        merged_lag = pd.merge_asof(
            lookup.sort_values('lookup_time'),
            cgm_for_merge[['timestamp', 'glucose']].sort_values('timestamp'),
            left_on='lookup_time',
            right_on='timestamp',
            direction='backward',
            tolerance=pd.Timedelta(minutes=5)
        )
        col_name = 'current_glucose' if lag == 0 else f'glucose_{lag}m_ago'
        df_grid[col_name] = merged_lag.set_index('prediction_timestamp').loc[df_grid['prediction_timestamp'], 'glucose'].values
    
    for lag in [5, 15, 30, 60]:
        df_grid[f'glucose_change_{lag}m'] = df_grid['current_glucose'] - df_grid[f'glucose_{lag}m_ago']
        
    df_grid['slope_30m'] = df_grid['glucose_change_30m'] / 30.0
    df_grid['slope_60m'] = df_grid['glucose_change_60m'] / 60.0
    
    if not is_online:
        df_grid['target_new_high_glucose_event'] = ((df_grid['current_glucose'] < 180) & (df_grid['target_high_glucose_120m'] == 1)).astype(float)
    
    # Rolling stats
    for window in ['15min', '30min', '60min', '120min']:
        roll = cgm_ts['glucose'].rolling(window)
        cgm_ts[f'cgm_mean_{window}'] = roll.mean()
        cgm_ts[f'cgm_std_{window}'] = roll.std()
        cgm_ts[f'cgm_min_{window}'] = roll.min()
        cgm_ts[f'cgm_max_{window}'] = roll.max()
        
    cols_to_merge = ['timestamp'] + [c for c in cgm_ts.columns if c.startswith('cgm_')]
    cgm_for_merge2 = cgm_ts.reset_index()[cols_to_merge]
    
    merged_roll = pd.merge_asof(
        df_grid[['prediction_timestamp']].sort_values('prediction_timestamp'),
        cgm_for_merge2.sort_values('timestamp'),
        left_on='prediction_timestamp',
        right_on='timestamp',
        direction='backward',
        tolerance=pd.Timedelta(minutes=5)
    )
    for c in cols_to_merge[1:]:
        df_grid[c] = merged_roll.set_index('prediction_timestamp').loc[df_grid['prediction_timestamp'], c].values

    # --- MEAL FEATURES ---
    if df_meals is not None and not df_meals.empty:
        df_meals = df_meals.sort_values('timestamp')
        df_meals['meal_time'] = df_meals['timestamp']
        
        merged_meals = pd.merge_asof(
            df_grid[['prediction_timestamp']].sort_values('prediction_timestamp'),
            df_meals[['timestamp', 'meal_time']].sort_values('timestamp'),
            left_on='prediction_timestamp',
            right_on='timestamp',
            direction='backward'
        )
        last_meal_time = merged_meals.set_index('prediction_timestamp').loc[df_grid['prediction_timestamp'], 'meal_time'].values
        df_grid['minutes_since_last_meal'] = (df_grid['prediction_timestamp'] - last_meal_time).dt.total_seconds() / 60.0
        
        # for proper rolling, we need meal grid covering at least 180m back
        if is_online:
            m_start = pd.to_datetime(online_timestamp) - pd.Timedelta(minutes=180)
            m_grid = pd.date_range(m_start, online_timestamp, freq='5min')
            df_grid_meals = pd.DataFrame({'prediction_timestamp': m_grid})
            df_grid_meals.set_index('prediction_timestamp', inplace=True)
        else:
            df_grid_meals = df_grid[['prediction_timestamp']].copy()
            df_grid_meals.set_index('prediction_timestamp', inplace=True)
        
        meal_agg = df_meals.set_index('timestamp')[['carbohydrate_g', 'protein_g', 'fat_g', 'fiber_g', 'calories']].resample('5min').sum()
        df_grid_meals = df_grid_meals.join(meal_agg)
        df_grid_meals = df_grid_meals.fillna(0)
        
        for m_col in ['carbohydrate_g', 'protein_g', 'fat_g', 'fiber_g', 'calories']:
            for w in ['30min', '60min', '120min', '180min']:
                df_grid_meals[f'{m_col.replace("_g", "")}_last_{w.replace("min", "m")}'] = df_grid_meals[m_col].rolling(w).sum()
                
        df_grid_meals['carb_exposure'] = df_grid_meals['carbohydrate_g'].ewm(halflife=12).mean() * 12
        df_grid_meals['recent_meal_outlier'] = ((df_grid_meals['carbohydrate_g'] > 500) | (df_grid_meals['fat_g'] > 300)).rolling('180min').max().fillna(0)
        
        df_grid_meals = df_grid_meals.drop(columns=['carbohydrate_g', 'protein_g', 'fat_g', 'fiber_g', 'calories'])
        if is_online:
            df_grid = df_grid.join(df_grid_meals, on='prediction_timestamp')
        else:
            df_grid = df_grid.join(df_grid_meals, on='prediction_timestamp')
    else:
        df_grid['minutes_since_last_meal'] = np.nan
        for m_col in ['carbohydrate', 'protein', 'fat', 'fiber', 'calories']:
            for w in ['30m', '60m', '120m', '180m']:
                df_grid[f'{m_col}_last_{w}'] = 0.0
        df_grid['carb_exposure'] = 0.0
        df_grid['recent_meal_outlier'] = 0.0

    # --- ACTIVITY FEATURES ---
    if df_activity is not None and not df_activity.empty:
        df_act = df_activity.set_index('timestamp').resample('5min').agg({
            'heart_rate': ['mean', 'std'],
            'activity_calories': 'sum'
        })
        df_act.columns = ['_'.join(c).strip('_') for c in df_act.columns]
        
        if is_online:
            a_start = pd.to_datetime(online_timestamp) - pd.Timedelta(minutes=120)
            a_grid = pd.date_range(a_start, online_timestamp, freq='5min')
            df_grid_act = pd.DataFrame({'prediction_timestamp': a_grid})
            df_grid_act.set_index('prediction_timestamp', inplace=True)
        else:
            df_grid_act = df_grid[['prediction_timestamp']].copy()
            df_grid_act.set_index('prediction_timestamp', inplace=True)
            
        df_grid_act = df_grid_act.join(df_act)
        
        df_grid_act['mean_HR_last_15m'] = df_grid_act['heart_rate_mean'].rolling('15min', min_periods=1).mean()
        df_grid_act['mean_HR_last_60m'] = df_grid_act['heart_rate_mean'].rolling('60min', min_periods=1).mean()
        df_grid_act['std_HR_last_60m'] = df_grid_act['heart_rate_mean'].rolling('60min', min_periods=1).std()
        df_grid_act['activity_calories_last_60m'] = df_grid_act['activity_calories_sum'].rolling('60min', min_periods=1).sum()
        df_grid_act['activity_calories_last_120m'] = df_grid_act['activity_calories_sum'].rolling('120min', min_periods=1).sum()
        
        if is_online:
            df_grid_act_sub = df_grid_act.loc[[pd.to_datetime(online_timestamp)]]
            df_grid['current_heart_rate'] = df_grid_act_sub['heart_rate_mean'].values
        else:
            df_grid['current_heart_rate'] = df_grid_act['heart_rate_mean'].values
            
        df_grid['hr_available'] = df_grid['current_heart_rate'].notna().astype(int)
        
        df_grid = df_grid.join(df_grid_act[['mean_HR_last_15m', 'mean_HR_last_60m', 'std_HR_last_60m', 
                                            'activity_calories_last_60m', 'activity_calories_last_120m']], 
                               on='prediction_timestamp')
    else:
        df_grid['hr_available'] = 0.0
        df_grid['current_heart_rate'] = np.nan
        for c in ['mean_HR_last_15m', 'mean_HR_last_60m', 'std_HR_last_60m', 'activity_calories_last_60m', 'activity_calories_last_120m']:
            df_grid[c] = np.nan

    # --- CIRCADIAN ---
    df_grid['hour_of_day'] = df_grid['prediction_timestamp'].dt.hour
    df_grid['sin_hour'] = np.sin(2 * np.pi * df_grid['hour_of_day'] / 24.0)
    df_grid['cos_hour'] = np.cos(2 * np.pi * df_grid['hour_of_day'] / 24.0)
    
    # --- STATIC FEATURES ---
    if df_static is not None and not df_static.empty:
        static_cols = ['age', 'gender', 'bmi', 'hba1c', 'fasting_glucose', 'fasting_insulin', 
                       'cholesterol', 'hdl', 'ldl', 'triglycerides', 'has_hypertension', 
                       'has_dyslipidemia', 'has_diabetes_medication', 'has_insulin']
        avail_static = [c for c in static_cols if c in df_static.columns]
        for c in avail_static:
            df_grid[c] = df_static.iloc[0][c]
            
    if not is_online:
        # Drop rows without sufficient targets or lookback
        df_grid = df_grid.dropna(subset=['target_glucose_120m', 'current_glucose', 'glucose_120m_ago'])
    else:
        # For online, we only need 'current_glucose' and 'glucose_120m_ago' to not be NaN for a valid prediction.
        # But we do NOT drop it here, so the caller can handle it
        pass
        
    return df_grid.reset_index(drop=True)

