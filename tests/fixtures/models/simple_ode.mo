model simple_ode
  "A simple exponential decay ODE for testing FMU generation"
  parameter Real lambda = 2.0 "Decay coefficient";
  Real y(start = 1.0) "State variable";
equation
  der(y) = -lambda * y;
end simple_ode;
