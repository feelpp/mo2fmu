model bouncing_ball
  "A simple model for testing FMI 3.0 with event management"

  // Parameters
  parameter Real e = 0.7 "Restitution coefficient (rebound elasticity)";
  parameter Real g = 9.81 "Gravity";

  // Inputs
  input Real wind_force(start = 0.0) "Vertical wind force (external)";

  // States (Continuous variables)
  Real h(start = 1.0, fixed=true) "Height (m)";
  Real v(start = 0.0, fixed=true) "Speed (m/s)";

  // Outputs
  output Real h_out "Height output for the log";
  output Integer bounce_count(start=0) "Rebound counter (Discrete Variable)";

equation
  // Connect to the output
  h_out = h;

  // Differential equations (Continuous system)
  der(h) = v;
  der(v) = -g + wind_force;

  // Event Management (Zero-Crossing)
  when h <= 0.0 and v < 0.0 then
    reinit(v, -e * v);                    // reversing speed results in energy loss
    bounce_count = pre(bounce_count) + 1; // increment the counter
  end when;

end bouncing_ball;
