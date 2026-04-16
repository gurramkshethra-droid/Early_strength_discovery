document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('#career-form');
  const marksInput = document.querySelector('#marks');
  const skillInput = document.querySelector('#skill');
  const interestSelect = document.querySelector('#interest');
  const messageBox = document.querySelector('#interest-message');
  const alertBox = document.querySelector('#form-alert');

  if (!form) {
    return;
  }

  const interestMessages = {
    coding: 'Focus on building projects, solving coding problems, and learning programming languages.',
    music: 'Practice consistently, learn music theory, and perform with other musicians.',
    sports: 'Train regularly, maintain good fitness, and work with a coach to improve.',
    dance: 'Refine your moves with practice, rhythm, and choreography training.',
    business: 'Develop communication, finance, and leadership skills to succeed in business.',
  };

  function updateInterestMessage() {
    const interest = interestSelect.value;
    messageBox.textContent = interestMessages[interest] || 'Choose an interest to see a quick career tip.';
  }

  updateInterestMessage();
  interestSelect.addEventListener('change', updateInterestMessage);

  form.addEventListener('submit', (event) => {
    const errors = [];
    alertBox.style.display = 'none';

    if (!marksInput.value.trim()) {
      errors.push('Please enter your marks.');
      marksInput.classList.add('input-error');
    } else {
      marksInput.classList.remove('input-error');
    }

    if (!skillInput.value.trim()) {
      errors.push('Please tell us your skill.');
      skillInput.classList.add('input-error');
    } else {
      skillInput.classList.remove('input-error');
    }

    if (errors.length > 0) {
      event.preventDefault();
      alertBox.textContent = errors.join(' ');
      alertBox.style.display = 'block';
    }
  });
});
