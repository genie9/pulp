MathJax.Hub.Config({
		tex2jax: {
		    inlineMath: [['$','$'], ['\\(','\\)']],
		    processEscapes: true
		    }
});

MathJax.Hub.Configured();

var SearchApp = angular.module("SearchApp", ["ngRoute", "angular-bootstrap-select", "angular-inview", "ui.bootstrap"]);

SearchApp.config(function($routeProvider){
	$routeProvider
	.when('/', {
		controller: 'SearchController',
		templateUrl: 'static/js/app/views/search.html'
	})
	.when('/settings', {
		controller: 'SettingsController',
		templateUrl: 'static/js/app/views/settings.html'
	})
	.when('/topic', {
		controller: 'TopicController',
		templateUrl: 'static/js/app/views/topic.html'
	})
	.when('/ratings', {
		controller: 'RatingsController',
		templateUrl: 'static/js/app/views/ratings.html'
	})
	.otherwise({
		redirectTo: '/settings'
	});
});

SearchApp.run(function($rootScope){
	$rootScope.settings = {
		participant_id: '',
		//task_type: 0,
		exploration_rate: 0.0,
		query_time: 15,
        query_iterations: 5,
        article_count: 20
		//study_type: 1
	};

	$rootScope.experiment_data = {
		articles: [],
		query: null,
		classifier_value: null
	};
});

SearchApp.filter("strip_tags", function(){
	return function(text){
		return String(text).replace(/<[^>]+>/gm, '');
	};
});

SearchApp.filter('html', function($sce){
  return function(input){
    return $sce.trustAsHtml(input);
  }
});

SearchApp.filter('ellipsis', function(){
	return function(text, size){
		if(String(text).length < size){
			return text;
		}else{
			return String(text).substring(0, size) + '...';
		}
	}
});

SearchApp.filter("synopsis", function(){
	return function(text){
		return ( String(text).length > 300 ? String(text).substring(0,300) + "..." : String(text) );
	}
});
