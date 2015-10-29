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

    $("#google-login").click(function(){
        $popup.bPopup();
        spinner.spin(target);
    });


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
        var url = $(this).data("url");
        var redirect = $(this).data("redirect");

        $.ajax({
            type: 'POST',
            url: url,
            success: function(response) {

                if (response.status === '200'){
                    window.location = redirect;
                }
            },
            error: function(response){
                spinner.stop();
                console.log("success", response.status);
            }

        });
    });

    window.googleCallback = function(authResult) {
        var STATE = $("#STATE").val();
        $("#google-login").addClass("hide");
        //$("#result").text(authResult);
        $.ajax({
            type: 'POST',
            url: '/ajax/gconnect?state=' + STATE,
            processData: 'false',
            contentType: 'application/octet-stream; charset=utf-8',
            data: authResult['code'],
            success: function (result) {
                console.log(result);
                if (result) {
                    $popup.bPopup();
                    spinner.spin(target);

                    $("#result").html('Login Successful!</br>' + result + '</br>Redirecting...');

                    setTimeout(function () {
                        window.location.href = "/catalog";
                    }, 4000);

                } else if (authResult['error']) {
                    console.log('There was an error: ' + authResult['error']);
                } else {
                    $("#result").html('Failed to make a server side call. Check your configuration and console.');
                }

            },
            error: function(result){
                $("#result").html(result.status + " " + result.statusText);
            }

        });
    }

}(window));
