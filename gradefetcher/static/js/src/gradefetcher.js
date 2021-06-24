/* Javascript for GradeFetcherXBlock. */
function GradeFetcherXBlock(runtime, element) {

    function updateGrade(result) {
        $('.block-description', element).html(result.htmlFormat);
    }

    var handlerUrl = runtime.handlerUrl(element, 'grade_user');

    $('#grade-me', element).click(
        function(eventObject) {
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
