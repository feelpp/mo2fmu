model ode_sin
  "ODE with a sinusoidal forcing term"
  parameter Real omega = 1 "Frequency of the sinusoidal input";
  Real y "State variable";
initial equation
  y = 0;
equation
  der(y) = sin(omega * time);
end ode_sin;