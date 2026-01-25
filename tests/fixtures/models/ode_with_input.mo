model ode_with_input
  "ODE with an external input for testing FMU with inputs"
  parameter Real lambda = 2.0 "Decay coefficient";
  input Real u "External input";
  Real y(start = 1.0) "State variable";
equation
  der(y) = -lambda * y + u;
end ode_with_input;
