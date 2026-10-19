import pandas as pd
import numpy as np
from pathlib import Path
from scipy.optimize import linear_sum_assignment
from sklearn.preprocessing import StandardScaler
from scipy.spatial.distance import cdist

def main():
    print("Starting Digital Twin Data Fusion...")
    
    # Paths
    project_root = Path(__file__).resolve().parent.parent
    interim_dir = project_root / "data" / "interim"
    processed_dir = project_root / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    # Load data
    synthea_df = pd.read_csv(interim_dir / "synthea_t2d_profiles.csv")
    cgmacros_df = pd.read_csv(interim_dir / "cgmacros_t2d_participants.csv")
    cgmacros_meals_df = pd.read_csv(interim_dir / "cgmacros_meals.csv")
    
    print(f"Loaded {len(synthea_df)} Synthea T2D profiles.")
    print(f"Loaded {len(cgmacros_df)} CGMacros T2D profiles.")
    
    # Define matching features
    # 'age', 'gender', 'bmi', 'hba1c', 'total_cholesterol', 'hdl', 'ldl', 'triglycerides'
    features_synthea = ['age', 'gender', 'bmi', 'hba1c', 'total_cholesterol', 'hdl', 'ldl', 'triglycerides']
    features_cgmacros = ['age', 'gender', 'bmi', 'hba1c', 'cholesterol', 'hdl', 'ldl', 'triglycerides']
    
    # Create aligned dataframes for matching
    df_s_match = synthea_df[features_synthea].copy()
    df_c_match = cgmacros_df[features_cgmacros].copy()
    
    # Rename CGMacros columns to match Synthea for consistency in the preprocessing array
    df_c_match.rename(columns={'cholesterol': 'total_cholesterol'}, inplace=True)
    
    # Encode gender (M=1, F=0)
    df_s_match['gender'] = df_s_match['gender'].map({'M': 1, 'F': 0})
    df_c_match['gender'] = df_c_match['gender'].map({'M': 1, 'F': 0})
    
    # Handle missing values (fill with median)
    df_s_match = df_s_match.fillna(df_s_match.median())
    df_c_match = df_c_match.fillna(df_c_match.median())
    
    # Convert to numpy arrays
    X_s = df_s_match[features_synthea].values
    X_c = df_c_match[features_synthea].values
    
    # Standardize features (fit on both together to have a common scale)
    scaler = StandardScaler()
    X_all = np.vstack([X_c, X_s])
    scaler.fit(X_all)
    
    X_c_scaled = scaler.transform(X_c)
    X_s_scaled = scaler.transform(X_s)
    
    # Calculate distance matrix (rows=CGMacros, cols=Synthea)
    # Using Euclidean distance on scaled features
    cost_matrix = cdist(X_c_scaled, X_s_scaled, metric='euclidean')
    
    # Apply linear sum assignment
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    
    # Create mapping
    mapping_records = []
    for i, c_idx in enumerate(row_ind):
        s_idx = col_ind[i]
        dist = cost_matrix[c_idx, s_idx]
        cg_id = cgmacros_df.iloc[c_idx]['cgmacros_subject_id']
        syn_id = synthea_df.iloc[s_idx]['source_patient_id']
        
        mapping_records.append({
            'cgmacros_subject_id': cg_id,
            'synthea_patient_id': syn_id,
            'matching_distance': dist
        })
        
    mapping_df = pd.DataFrame(mapping_records)
    
    # Sort by matching distance to assign best matches first
    mapping_df = mapping_df.sort_values('matching_distance').reset_index(drop=True)
    
    mapping_records_sorted = []
    for i, row in mapping_df.iterrows():
        mapping_records_sorted.append({
            'digital_twin_id': f"DT-{i+1:02d}",
            'cgmacros_subject_id': row['cgmacros_subject_id'],
            'synthea_patient_id': row['synthea_patient_id'],
            'matching_distance': row['matching_distance']
        })
    mapping_df = pd.DataFrame(mapping_records_sorted)
    
    # Select top 3 as demo candidates
    mapping_df['is_demo_candidate'] = False
    mapping_df.loc[0:2, 'is_demo_candidate'] = True
    
    # Audit meal outliers
    # We flag any twin where their CGMacros subject has extreme meals
    extreme_carbs = cgmacros_meals_df[cgmacros_meals_df['carbohydrate_g'] > 500]['cgmacros_subject_id'].unique()
    extreme_fats = cgmacros_meals_df[cgmacros_meals_df['fat_g'] > 300]['cgmacros_subject_id'].unique()
    
    outlier_subjects = set(extreme_carbs) | set(extreme_fats)
    
    mapping_df['has_meal_outliers'] = mapping_df['cgmacros_subject_id'].isin(outlier_subjects)
    
    mapping_df.to_csv(processed_dir / "twin_mapping.csv", index=False)
    
    # Create twin_registry.csv
    mapping_df.to_csv(processed_dir / "twin_registry.csv", index=False)
    
    # Create twin_static_profiles.csv
    # Merge Synthea metadata and CGMacros bio data
    static_profiles = []
    
    for _, row in mapping_df.iterrows():
        dt_id = row['digital_twin_id']
        cg_id = row['cgmacros_subject_id']
        syn_id = row['synthea_patient_id']
        
        c_data = cgmacros_df[cgmacros_df['cgmacros_subject_id'] == cg_id].iloc[0]
        s_data = synthea_df[synthea_df['source_patient_id'] == syn_id].iloc[0]
        
        # Combine data
        profile = {
            'digital_twin_id': dt_id,
            'cgmacros_subject_id': cg_id,
            'synthea_patient_id': syn_id,
            'age': c_data['age'], # Use primary physiological identity
            'gender': c_data['gender'],
            'bmi': c_data['bmi'],
            'body_weight_kg': c_data['body_weight_kg'],
            'hba1c': c_data['hba1c'],
            'fasting_glucose': c_data['fasting_glucose'],
            'cholesterol': c_data['cholesterol'],
            'hdl': c_data['hdl'],
            'ldl': c_data['ldl'],
            'triglycerides': c_data['triglycerides'],
            # Synthea medical context
            'has_hypertension': s_data['has_hypertension'],
            'has_dyslipidemia': s_data['has_dyslipidemia'],
            'has_diabetes_medication': s_data['has_diabetes_medication'],
            'has_insulin': s_data['has_insulin'],
            'diabetes_medication_count': s_data['diabetes_medication_count'],
            'synthea_profile_completeness': s_data['profile_completeness']
        }
        static_profiles.append(profile)
        
    profiles_df = pd.DataFrame(static_profiles)
    profiles_df.to_csv(processed_dir / "twin_static_profiles.csv", index=False)
    
    print(f"Created Twin Registry with {len(mapping_df)} composite patients.")
    print(f"Saved to {processed_dir}")

if __name__ == '__main__':
    main()
