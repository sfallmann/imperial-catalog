#Imperial Catalog - Project 3 Full Stack Nanodegree

###Requirements
* Python 2.7+ https://www.python.org/
* Install Vagrant, VirtualBox, and clone the fullstack-nanodegree-vm.
  Full instructions located here https://www.udacity.com/wiki/ud197/install-vagrant
* Instead of using the vm, you can install the packages in the included requirements.txt
  as well.  I recommend using pip to install. https://pypi.python.org/pypi/pip/
* Facebook and Google client secret and client id to authenticate
    * Both will be for the web
    * For Google:  https://console.developers.google.com/
    * For Facebook: https://developers.facebook.com/docs/facebook-login/web
    * Udacity course for Authentication and Authorization covers creating the apps
      https://www.udacity.com/course/viewer#!/c-ud330/l-3967218625/e-3963648613/m-3963648614



###Install:
    * Download or clone this repository
    * cd to the folder the files were extracted\copied to
    * Get the json file for the registered Google app (see above)
      and copy it to the folder and name it client_secrets.json
    * Using your text editor of choice create the fb_client_secrets.json:
        {
          "web": {
            "app_id": YOUR APP ID",
            "app_secret": "YOUR APP SECRET"
          }
        }
    * Edit templates/login.html
        * Look for <button class="g-signin" data-scope="openid email" data-clientid="57915...
        * Replace the value in data-clientid to your Google app id
    * Edit js/lib/main.js
        * Look for:
            // Initialize the Facebook SDK
            window.fbAsyncInit = function() {
                FB.init({
                appId      : '446841215515973',
                cookie     : true,  // enable cookies to allow the server to access
                                    // the session
                xfbml      : true,  // parse social plugins on this page
                version    : 'v2.2' // use version 2.2
                });

            };
        * Replace the value in appId with the app id for your Facebook app
    * At the command line enter:
        * python popuplate_db.py to populate the db with starter data
        * python application.py to start the application

###Use:
    * Browse to http://localhost:8000
    * For IE, allow this site (http://localhost:8000) as a trusted site.  If you don't do this,
      authentication will not work.

###The catalog's theme is based on the Galactic Empire in the Star Wars Universe.
   The app is fully responsive and will work well on mobile devices (only tested Android devices although
   it should work fine on iOS)
