model multi_state
  "Model with multiple state variables for testing"
  parameter Real k1 = 1.0 "Coefficient 1";
  parameter Real k2 = 2.0 "Coefficient 2";
  Real x(start = 1.0) "First state variable";
  Real y(start = 0.0) "Second state variable";
equation
  der(x) = -k1 * x + k2 * y;
  der(y) = k1 * x - k2 * y;
end multi_state;
