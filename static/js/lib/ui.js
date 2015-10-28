(function(){
    //  https://css-tricks.com/transitions-only-after-page-load/  for delaying transitions after page load
    $(document).load(function() {
        $("body").removeClass("preload");
    });

    var spinOpts = {
        lines: 13 // The number of lines to draw
        , length: 28 // The length of each line
        , width: 14 // The line thickness
        , radius: 42 // The radius of the inner circle
        , scale: 1 // Scales overall size of the spinner
        , corners: 1 // Corner roundness (0..1)
        , color: '#FFFFFF' // #rgb or #rrggbb or array of colors
        , opacity: 0.8 // Opacity of the lines
        , rotate: 0 // The rotation offset
        , direction: 1 // 1: clockwise, -1: counterclockwise
        , speed: 1 // Rounds per second
        , trail: 60 // Afterglow percentage
        , fps: 20 // Frames per second when using setTimeout() as a fallback for CSS
        , zIndex: 99999 // The z-index (defaults to 2000000000)
        , className: 'spinner' // The CSS class to assign to the spinner
        , top: '50%' // Top position relative to parent
        , left: '50%' // Left position relative to parent
        , shadow: false // Whether to render a shadow
        , hwaccel: false // Whether to use hardware acceleration
        , position: 'absolute' // Element positioning
    }

    var popupOpts = {
        escClose: false,
        modalClose: false,
        modalColor: '#841F27'
    }

    var target = document.getElementById('main')
    var spinner = new Spinner(spinOpts);
    var $popup = $("#popup");


    $("#addItem").click(function(){
        var url = $(this).data("url");

        window.location=url;
    });


    $("#login-button").click(function(){
        /*
        $popup.bPopup();
        spinner.spin(target);
        var url = $(this).data("url");
        window.location = url;
        */

        var $auth = $("#authenticate");
        $auth.toggleClass("hide");
        $auth.bPopup();
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


}());
