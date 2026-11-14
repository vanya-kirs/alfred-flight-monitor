from __future__ import annotations

import json
import subprocess
from pathlib import Path


INDEX = Path(__file__).parents[1] / "src" / "alfred_flights" / "web" / "index.html"


def test_switching_to_login_disables_hidden_registration_fields() -> None:
    html = INDEX.read_text(encoding="utf-8")
    function_source = html.split("    function setRegisterMode(mode) {", 1)[1].split(
        "    function completeAccountSession", 1
    )[0]
    function_source = "function setRegisterMode(mode) {" + function_source
    harness = r"""
const fs = require('fs');
const functionSource = fs.readFileSync(0, 'utf8');
const elements = new Proxy({}, {
  get(target, key) {
    if (!target[key]) target[key] = {hidden: false, required: true, disabled: false, textContent: '', autocomplete: ''};
    return target[key];
  }
});
const document = {querySelector(selector) { return elements[selector]; }};
let registerMode = 'register';
eval(functionSource);
elements['#register-password-confirmation'].value = '123';
setRegisterMode('login');
process.stdout.write(JSON.stringify({
  confirmation: elements['#register-password-confirmation'],
  consent: elements['#register-bank-consent']
}));
"""

    result = subprocess.run(
        ["node", "-e", harness],
        input=function_source,
        text=True,
        capture_output=True,
        check=True,
    )
    state = json.loads(result.stdout)

    assert state["confirmation"]["required"] is False
    assert state["confirmation"]["disabled"] is True
    assert state["consent"]["required"] is False
    assert state["consent"]["disabled"] is True


def test_logout_clears_browser_identity_but_keeps_persistent_account() -> None:
    html = INDEX.read_text(encoding="utf-8")
    function_source = html.split("    function logoutAccount() {", 1)[1].split(
        "    document.querySelector('#account-button')", 1
    )[0]
    function_source = "function logoutAccount() {" + function_source
    harness = r"""
const fs = require('fs');
const functionSource = fs.readFileSync(0, 'utf8');
const values = new Map([['alfred_account_id', 'account-1'], ['alfred_profile_name', 'Иван Иванов']]);
const sessionStorage = {removeItem(key) { values.delete(key); }};
let accountId = 'account-1';
let registeredName = 'Иван Иванов';
const accountDialog = {hidden: false};
const registerGate = {hidden: true};
let selectedMode = '';
let buttonUpdated = false;
const setRegisterMode = mode => { selectedMode = mode; };
const updateAccountButton = () => { buttonUpdated = true; };
const toast = () => {};
eval(functionSource);
logoutAccount();
process.stdout.write(JSON.stringify({
  accountId,
  registeredName,
  storedId: values.get('alfred_account_id') || null,
  storedName: values.get('alfred_profile_name') || null,
  accountDialogHidden: accountDialog.hidden,
  registerGateHidden: registerGate.hidden,
  selectedMode,
  buttonUpdated
}));
"""

    result = subprocess.run(
        ["node", "-e", harness],
        input=function_source,
        text=True,
        capture_output=True,
        check=True,
    )
    state = json.loads(result.stdout)

    assert state == {
        "accountId": "",
        "registeredName": "",
        "storedId": None,
        "storedName": None,
        "accountDialogHidden": True,
        "registerGateHidden": False,
        "selectedMode": "login",
        "buttonUpdated": True,
    }
