$(document).ready(function() {

    var SizePrefixes = ' KMGTPEZYXWVU';
    function GetHumanSize(size) {
      if(size <= 0) return 'Unlimited';
      var t2 = Math.min(Math.floor(Math.log(size)/Math.log(1024)), 12);
      return (Math.round(size * 100 / Math.pow(1024, t2)) / 100) + SizePrefixes.charAt(t2).replace(' ', '') + 'B';
    }

    $(function() {
        $( ".x-slider" ).slider( {
            range: true,
            min: 0,
            max: 256,
            step: 1,
            values: [ 0, 256 ],
            create: function(event, ui) {
                $(this).slider("enable");
                //$(this).slider('values', $(this).parent().find("amount").val() );
                //$.get(sbRoot + '/config/quality/getQualitySizes', { quality: $(this).data('id') });
            },
            slide: function( event, ui ) {
                // scale size to megabyte so the ranges make sense
                var minSize = 1024 * 1024 * ui.values[0];
                var maxSize = 1024 * 1024 * ui.values[1];

                var minThirty = GetHumanSize(minSize * 30);
                var maxThirty = GetHumanSize(maxSize * 30);
                $(this).parent().find('[name="thirtyMinuteMinSize"]').html(minThirty);
                $(this).parent().find('[name="thirtyMinuteMaxSize"]').html(maxThirty);

                var minSixty = GetHumanSize(minSize * 60);
                var maxSixty = GetHumanSize(maxSize * 60);
                $(this).parent().find('[name="sixtyMinuteMinSize"]').html(minSixty);
                $(this).parent().find('[name="sixtyMinuteMaxSize"]').html(maxSixty);

                // internal scale, how many mb per 1 min of runtime
                $(this).parent().find('.sizeRange').val( $(this).data('id') + ":" + ui.values[ 0 ] + "-" + ui.values[ 1 ] );
            }
        });
        // $( "#amount" ).val( GetHumanSize($( "#slider-range" ).slider( "values", 0 )) + " - " + GetHumanSize($( "#slider-range" ).slider( "values", 1 )) );
    });

});
