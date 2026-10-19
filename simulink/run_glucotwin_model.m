function [t, Y] = run_glucotwin_model(params, initial_state, duration_min)
% run_glucotwin_model - Solves the simplified ODE minimal model
% Y(1) = G (Blood glucose mg/dL)
% Y(2) = X (Effective insulin action 1/min)
% Y(3) = D (Gut carbohydrate compartment mg)

    tspan = [0 duration_min];
    y0 = [initial_state.G; initial_state.X; initial_state.D];
    [t, Y] = run_glucotwin_model(params, initial_state, duration_min);
    
    [t, Y] = ode45(@(t,y) glucotwin_odes(t, y, params), tspan, y0);
end

function dydt = glucotwin_odes(t, y, p)
    G = y(1);
    X = y(2);
    D = y(3);
    
    % Gut absorption (Rate of Appearance)
    Ra = (p.f * p.k_abs * D) / p.Vg;
    
    % ODEs
    dG_dt = -(p.Sg + X) * G + p.Sg * p.Gb + Ra;
    
    % Effective insulin action (driven by glucose > Gb)
    % Simplified beta-cell response proxy: insulin secretion is proportional to glucose above baseline
    I_sec = max(0, p.Si * (G - p.Gb)); 
    dX_dt = -p.p2 * X + p.p2 * I_sec;
    
    % Gut compartment depletion
    dD_dt = -p.k_abs * D;
    
    dydt = [dG_dt; dX_dt; dD_dt];
end
