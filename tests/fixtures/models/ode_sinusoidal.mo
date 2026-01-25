model ode_sinusoidal
  "ODE with a sinusoidal forcing term"
  parameter Real omega = 1.0 "Frequency of the sinusoidal input";
  Real y(start = 0.0) "State variable";
equation
  der(y) = sin(omega * time);
end ode_sinusoidal;
