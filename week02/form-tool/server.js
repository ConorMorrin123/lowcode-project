const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware to parse URL-encoded bodies (from HTML forms)
app.use(express.urlencoded({ extended: true }));

// Set EJS as the template engine
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// Email validation helper function
function isValidEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

// GET Route: Render the Contact Form
app.get('/', (req, res) => {
  res.render('form', { 
    errors: {}, 
    formData: { name: '', email: '', message: '' } 
  });
});

// POST Route: Process Form Submission with Server-Side Validation
app.post('/contact', (req, res) => {
  const { name, email, message } = req.body;
  const errors = {};

  // 1. Validate Name: Reject empty or whitespace-only input
  if (!name || name.trim().length === 0) {
    errors.name = 'Name cannot be empty or consist only of spaces.';
  }

  // 2. Validate Email: Check format and non-empty
  if (!email || email.trim().length === 0) {
    errors.email = 'Email address is required.';
  } else if (!isValidEmail(email.trim())) {
    errors.email = 'Please enter a valid email address (e.g., user@example.com).';
  }

  // 3. Validate Message: Reject empty or whitespace-only input
  if (!message || message.trim().length === 0) {
    errors.message = 'Message cannot be empty or consist only of spaces.';
  }

  // If there are validation errors, re-render form with errors and previous input
  if (Object.keys(errors).length > 0) {
    return res.status(400).render('form', {
      errors,
      formData: { name, email, message }
    });
  }

  // Sanitize data before using/saving
  const sanitizedData = {
    name: name.trim(),
    email: email.trim(),
    message: message.trim()
  };

  // Render Confirmation Page on success
  res.render('confirmation', { data: sanitizedData });
});

app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});