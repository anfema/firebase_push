Firebase cloud messaging for Django with original Google SDK.

## Installation

1. Requirements
  - Add `firebase_push` to your `requirements.txt`/`Pipfile`/`pyproject.toml`
  - Import the default settings at the end of your `settings.py`:
    ```python
    from firebase_push.conf.settings import *
    ```
  - Override default settings if needed (see next section)
2. URLs
  - Add urls to your `urlpatterns` in `urls.py`
    ```python
    from firebase_push.conf.urls import urlpatterns as firebase_push_urlpatterns

    urlpatterns += firebase_push_urlpatterns
    ```
3. Application
  - Add `firebase_push` and `rest_framework` to your `INSTALLED_APPS`
    ```python
    INSTALLED_APPS = [
        "firebase_push",
        "rest_framework",
        ...
    ]
    ```
4. Run `manage.py migrate`
5. Do not forget to configure REST-Framework authentication (or supply CSRF
   Tokens when calling the API :S)

## Configuration

### Required

Set environment variable `GOOGLE_APPLICATION_CREDENTIALS` to the path to your
service account JSON file:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service_account.json
```

#### To generate a private key file for your service account:

1. In the Firebase console, open **Settings** > [Service Accounts](https://console.firebase.google.com/project/_/settings/serviceaccounts/adminsdk).
2. Click **Generate New Private Key**, then confirm by clicking **Generate Key**.
3. Securely store the JSON file containing the key.

### Optional

- `FCM_USER_MODEL`: (path) override this if you need to attach anything other
  than the Django defined user model (configured by `settings.AUTH_USER_MODEL`)
  to your FCM device. (Note: if you override this, the user cannot be fetched
  from the session so you'll need to override the next option too.)
- `FCM_FETCH_USER_FUNCTION`: (path) path to the function to call in your code
  to fetch a user id to attach to the request. Will be called with the Django
  `request` as single parameter, expected to return an id to a DB model
  instance of `FCM_USER_MODEL`.


## Running

// TODO: Add information about celery

## Usage

// TODO: Document API