jQuery(document).ready(function($) {
	//
	// Slide in Side Navigation inspired by CodyHouse article:
	//

	//open navigation clicking the menu icon
	$('.cd-nav-trigger').on('click', function(event){
		event.preventDefault();
		toggleNav(true);
	});
	//close the navigation
	$('.cd-close-nav, .cd-overlay').on('click', function(event){
		event.preventDefault();
		toggleNav(false);
	});
	//select a new section
	$('.cd-nav li').on('click', function(event){
		var target = $(this);
		var sectionTarget = target.data('menu');
		if( !target.hasClass('cd-selected') ) {
			//if user has selected a section different from the one alredy visible
			//update the navigation -> assign the .cd-selected class to the selected item
			target.addClass('cd-selected').siblings('.cd-selected').removeClass('cd-selected');
		}
		toggleNav(false);
	});

	function toggleNav(bool) {
		$('.cd-nav-container, .cd-overlay').toggleClass('is-visible', bool);
		$('main').toggleClass('scale-down', bool);
	}

	//
	// Click-able ingredient checklist inspired by:
	// ...
	//

	// Check item when clicked
	//open navigation clicking the menu icon
	$('ul li.ingredient').on('click', function(event){
	  console.info("click");
	  console.log(event);
		event.preventDefault();
	  // $(event.target).addClass('checked');
		$(event.target).toggleClass('checked', !event.target.classList.contains('checked'));
	  console.log(event.target.classList);
	  console.log($(event.target).attr('id'));

	  console.info('url:');
	  console.log(window.location.href);

	  window.history.pushState(null, null, window.location.href + '__hello_world');
	  console.log('test push state');
	});
});