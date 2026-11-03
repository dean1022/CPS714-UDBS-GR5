// Personal information page (US-15): only the preferred name and pronouns can be changed
const form = document.querySelector('#profile-form');
const nameInput = document.querySelector('#display-name');
const pronounsInput = document.querySelector('#pronouns');
const saveButton = document.querySelector('#save-profile');

function showProfile(profile) {
  document.querySelector('#legal-name').textContent = profile.first_name + ' ' + profile.last_name;
  document.querySelector('#university-id').textContent = profile.university_id;
  document.querySelector('#email').textContent = profile.email;
  document.querySelector('#status').textContent = profile.status === 'faculty' ? 'Faculty' : 'Student';
  nameInput.value = profile.display_name || '';
  pronounsInput.value = profile.pronouns || '';
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!nameInput.value.trim()) {
    showPageError(new Error('Please enter a preferred name.'));
    nameInput.focus();
    return;
  }
  saveButton.disabled = true;
  try {
    const data = await libraryRequest('profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ display_name: nameInput.value, pronouns: pronounsInput.value }),
    });
    showProfile(data.profile);
    showPageMessage(data.message);
  } catch (error) {
    showPageError(error);
  }
  saveButton.disabled = false;
});

(async () => {
  try {
    await checkLogin();
    const data = await libraryRequest('profile');
    showProfile(data.profile);
    document.querySelector('#private-content').hidden = false;
  } catch (error) {
    showPageError(error);
  }
})();
