/* Javascript for GradeFetcherXBlock. */
function GradeFetcherXBlock(runtime, element) {

    function updateGrade(result) {
        $('.block-description', element).html(result.htmlFormat);
        $(".block-button-loading").css('display', 'none');
        $("#grade-me").css('display', "block")
    }

    var handlerUrl = runtime.handlerUrl(element, 'grade_user');

    $('#grade-me', element).click(
        function(eventObject) {
            $(".block-button-loading").css('display', 'block'),
            $("#grade-me").css('display', "none"),
            $.ajax({
                type: "POST",
                url: handlerUrl,
                data: JSON.stringify({}),
                success: updateGrade
            });
        });

    $(function ($) {
    });
}
