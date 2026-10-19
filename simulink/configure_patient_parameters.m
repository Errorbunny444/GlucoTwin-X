function p = configure_patient_parameters(static_snapshot)
% configure_patient_parameters - Derive physiological parameters from static twin state
% This is a simplified reduced-order minimal model parameterization.
% Note: NOT a clinically validated patient-specific simulator.

    % Nominal parameters (Bergman Minimal Model inspired)
    % G: Glucose concentration (mg/dL)
    % X: Effective insulin action (1/min)
    % D: Gut carbohydrate absorption compartment (mg)

    p = struct();
    
    % Baseline glucose from static profile or default to 100
    if isfield(static_snapshot, 'fasting_glucose') && static_snapshot.fasting_glucose > 0
        p.Gb = static_snapshot.fasting_glucose;
    else
        p.Gb = 100.0;
    end
    
    % Insulin sensitivity (Si) proxy: reduced if BMI is high or HbA1c is high
    Si_nominal = 0.001; 
    bmi_factor = max(0.5, 25.0 / max(20.0, static_snapshot.bmi));
    hba1c_factor = max(0.5, 5.5 / max(5.0, static_snapshot.hba1c));
    p.Si = Si_nominal * bmi_factor * hba1c_factor;
    
    % Glucose effectiveness (Sg): ability of glucose to promote its own disposal
    p.Sg = 0.015;
    
    % Insulin action kinetics (p2): rate of clearance of insulin action
    p.p2 = 0.02;
    
    % Gut absorption rate (k_abs): rate of appearance of meal carbs
    p.k_abs = 0.03;
    
    % Volume of distribution for glucose (Vg) in dL
    weight_kg = static_snapshot.bmi * ((1.7)^2); % assume 1.7m height if weight unknown
    p.Vg = weight_kg * 0.15 * 10; % rough approx ~15% of body weight in dL
    
    % Meal bioavailability factor (f)
    p.f = 0.8;
end
