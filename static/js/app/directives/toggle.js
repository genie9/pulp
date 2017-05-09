SearchApp.directive('toggle', function(){
    return {
        restrict: 'A',
        link: function(scope, element, attrs){
            if (attrs.toggle=="popover"){
                $(element).popover({
                    container:'body',
                    html:true,
                    placement:'bottom'
                });
            }
        }
    };
})
