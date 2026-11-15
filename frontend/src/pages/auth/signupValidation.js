export function validateSignup({ username, password, confirmation }) {
  const errors = {};
  if (!/^[a-zA-Z0-9_.-]{3,50}$/.test(username.trim())) {
    errors.username = "Use 3–50 letters, numbers, periods, underscores, or hyphens.";
  }
  if (Array.from(password).length < 12 || Array.from(password).length > 128) {
    errors.password = "Use 12–128 characters.";
  } else if (!/\p{L}/u.test(password) || !/[\p{N}\p{P}\p{S}]/u.test(password)) {
    errors.password = "Use a letter and at least one number or symbol.";
  }
  if (!confirmation) errors.confirmation = "Confirm your password.";
  else if (confirmation !== password) errors.confirmation = "The passwords do not match.";
  return errors;
}
