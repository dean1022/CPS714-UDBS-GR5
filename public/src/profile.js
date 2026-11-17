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

// Borrowing privileges for this role (Sprint 4: student vs faculty)
function showPrivileges(user) {
  const box = document.querySelector('#privileges');
  if (!box || !user) return;
  const rows = [
    ['Active loans', `Up to ${user.loan_limit}`],
    ['Active holds', `Up to ${user.hold_limit}`],
    ['Loan length', user.is_staff ? 'No due date' : '14 days, renew up to 2 times'],
    ['Hold queue', user.is_staff ? 'Ahead of student holds' : 'First come, first served'],
  ];
  box.innerHTML = `<h2>Borrowing privileges <span class="role-chip${user.is_staff ? ' faculty' : ''}">${safeText(user.role_label)}</span></h2>
    <dl class="book-facts profile-facts">${rows.map(([k, v]) => `<div><dt>${k}</dt><dd>${safeText(v)}</dd></div>`).join('')}</dl>`;
  box.hidden = false;
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
    const user = await checkLogin();
    showPrivileges(user);
    const data = await libraryRequest('profile');
    showProfile(data.profile);
    document.querySelector('#private-content').hidden = false;
  } catch (error) {
    showPageError(error);
  }
})();
