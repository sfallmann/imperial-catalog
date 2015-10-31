(function(window){
    //  https://css-tricks.com/transitions-only-after-page-load/  for delaying transitions after page load
    $(document).load(function() {
        $("body").removeClass("preload");
    });

    var spinOpts = {
        lines: 13,
        length: 28,
        width: 14,
        radius: 42,
        scale: 1,
        corners: 1,
        color: '#FFFFFF',
        opacity: 0.8,
        rotate: 0,
        direction: 1,
        speed: 1,
        trail: 60,
        top: '50%',
        left: '50%',
        hwaccel: false,
        position: 'absolute'
    }

    var popupOpts = {
        escClose: false,
        modalClose: false,
        modalColor: '#841F27'
    }

    var target = document.getElementById('main')
    var spinner = new Spinner(spinOpts);
    var $popup = $("#popup");
    var $deletePopup;


    $("#addItem").click(function(){
        var url = $(this).data("url");
        window.location=url;
    });


    $("#delete-button").click(function(){
        $("#delete-confirm").toggleClass("hide");
        $deletePopup = $('#delete-confirm').bPopup();
    });

    $("#edit-button").click(function(){
        var $editPage = $(this).data("url");
        window.location = $editPage;
    });


    $("#close-popup").click(function(){
        $("#delete-confirm").toggleClass("hide");
        $deletePopup.close();
    });

    $("#login-button").click(function(){
        var url = $(this).data("url");
        window.location = url;
    });

    $("#logout-button").click(function(){
        $popup.bPopup();
        spinner.spin(target);
        window.location = '/disconnect';

    });

    window.googleCallback = function(authResult) {
        var csrf_token = $("#csrf_token").val();
        console.log(csrf_token);
        $(".login-btn").addClass("hide");
        $("#login-button").attr("disabled", "true");
        spinner.spin(target);
        $.ajax({
            type: 'POST',
            url: '/ajax/gconnect',
            processData: 'false',
            data: { 'code': authResult['code'], '_csrf_token': $("#csrf_token").val() },
            success: function (result) {
                console.log(result);
                if (result) {


                    $("#result").html('Login Successful!</br>' + result + '</br>Redirecting...');

                    setTimeout(function () {
                        window.location.href = "/catalog";
                    }, 4000);

                } else if (authResult['error']) {
                    console.log('There was an error: ' + authResult['error']);
                } else {
                    $("#result").html('Failed to make a server side call. Check your configuration and console.');
                    $("#login-button").attr("disabled", "false");
                    spinner.stop();
                }

            },
            error: function(result){
                $("#result").html(result.status + " " + result.statusText);
            }

        });
    }




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

    // Load the Facebook SDK asynchronously
    (function(d, s, id) {
        var js, fjs = d.getElementsByTagName(s)[0];
        if (d.getElementById(id)) return;
        js = d.createElement(s); js.id = id;
        js.src = "//connect.facebook.net/en_US/sdk.js";
        fjs.parentNode.insertBefore(js, fjs);
    }(document, 'script', 'facebook-jssdk'));

    window.sendFBToken = function() {
        var access_token = FB.getAuthResponse()['accessToken'];
        $(".login-btn").addClass("hide");
        console.log(access_token);
        console.log('Welcome!  Fetching your information.... ', $("#csrf_token").val());
        FB.api('/me', function(response) {
            console.log(response);

            $("#login-button").attr("disabled", "true");
            spinner.spin(target);

            console.log('Successful login for: ' + response.name);
            $.ajax({
                type: 'POST',
                url: '/ajax/fbconnect',
                data: { 'access_token': access_token, '_csrf_token': $("#csrf_token").val() },
                success: function(result) {

                    // Handle or verify the server response if necessary.
                    if (result) {
                        $('#result').html('Login Successful!</br>'+ result + '</br>Redirecting...');
                        setTimeout(function() {
                            window.location.href = "/catalog";
                        }, 4000);

                    }
                    else{
                        $('#result').html('Failed to make a server-side call. Check your configuration and console.');
                        $("#login-button").attr("disabled", "false");
                        spinner.stop();
                    }
                }

            });

        });
    }

}(window));
