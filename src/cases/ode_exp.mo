model ode_exp
  "The 'classic' ODE"
  parameter Real lambda=2 "Coefficient";
  Real y "y";
initial equation
  y = 1;
equation
  der(y) = -lambda*y;
end ode_exp;