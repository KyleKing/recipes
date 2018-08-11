jQuery( document ).ready( ( $ ) => {
  //
  // Slide in Side Navigation inspired by CodyHouse article:
  //

  function toggleNav( bool ) {
    $( '.cd-nav-container, .cd-overlay' ).toggleClass( 'is-visible', bool )
    $( 'main' ).toggleClass( 'scale-down', bool )
  }
  // Open navigation clicking the menu icon
  $( '.cd-nav-trigger' ).on( 'click', ( event ) => {
    event.preventDefault()
    toggleNav( true )
  } )
  // Close the navigation
  $( '.cd-close-nav, .cd-overlay' ).on( 'click', ( event ) => {
    event.preventDefault()
    toggleNav( false )
  } )
  // Select a new section
  $( '.cd-nav li' ).on( 'click', function() {
    var target = $( this )
    // var sectionTarget = target.data('menu');
    if ( !target.hasClass( 'cd-selected' ) ) {
      // if user has selected a section different from the one alredy visible
      // update the navigation -> assign the .cd-selected class to the selected item
      target.addClass( 'cd-selected' ).siblings( '.cd-selected' ).removeClass( 'cd-selected' )
    }
    toggleNav( false )
  } )


  //
  // Click-able ingredient checklist with saved state in URL
  //

  function parseURL( fullUrl ) {
    // Initialize URL components for export
    var urlComps = new Object()
    urlComps.tagBR = '\?tag='
    urlComps.ingBR = '\?ingredients='
    urlComps.ingredients = []
    urlComps.tag = ''
    // Separate ingredient list from rest of URL
    var components = fullUrl.split( '\?' )
    for ( var idx = 0; idx < components.length; idx ++ ) {
      var comp = '?' + components[idx]
      if ( comp.indexOf( urlComps.ingBR ) >= 0 ) {
        // Create list of ingredients from URL
        urlComps.ingredients = comp.split( urlComps.ingBR )[1].split( ',' )
        // console.log('urlComps.ingredients: ' + urlComps.ingredients);
        // console.log(comp.split(urlComps.ingBR));
      } else if ( comp.indexOf( urlComps.tagBR ) >= 0 ) {
        // Parse the linked recipe tag
        urlComps.tag = comp.split( urlComps.tagBR )[1]
        // console.log('urlComps.tag: ' + urlComps.tag);
        // console.log(comp.split(urlComps.tagBR));
      } else {
        // FIXME: Without the tag, the URL can't be updated...
        urlComps.baseUrl = comp.slice( 1 ).split( '#' )[0] + '#'
        // console.log('urlComps.baseUrl: ' + urlComps.baseUrl);
      }
    }
    return( urlComps )
  }

  // Check item when clicked
  //  open navigation clicking the menu icon
  $( '.ingredient' ).on( 'click', ( event ) => {
    // For debugging:
    var fullUrl = window.location.href
    if ( fullUrl.search( 'Users/kyleking' ) )
      console.log( 'Current url: ' + fullUrl )
      // console.log(event);
      // console.log(event.target.classList);

    // Either add or remove ingredient ID and set check box value appropriately
    var comps = parseURL( fullUrl )
    var ingID = $( event.target ).attr( 'id' )
    if ( event.currentTarget.checked ) {
      if ( comps.ingredients.length === 0 )
        comps.ingredients = [ingID]
      else
        comps.ingredients.push( ingID )

    } else {
      // console.log('idx:');
      // console.log(ingID);
      // console.log(comps.ingredients);
      // console.log(comps.ingredients.indexOf(ingID));
      comps.ingredients.splice( comps.ingredients.indexOf( ingID ), 1 )
    }
    comps.ingredients.sort()
    var finalUrl = comps.baseUrl + comps.ingBR + comps.ingredients.join( ',' ) +
                   comps.tagBR + comps.tag
    window.history.pushState( null, null, finalUrl )
    console.log( 'Final url: ' + finalUrl + '\n' )
  } )

  // Read ingredients state and update check boxes:
  var fullUrl = window.location.href
  var ingredients = parseURL( fullUrl ).ingredients
  for ( var idx = 0; idx < ingredients.length; idx++ ) {
    var ingID  = ingredients[idx]
    if ( fullUrl.search( 'file:/' ) ) {
      console.log( 'Toggling? #' + ingID )
      console.log( $( '#' + ingID ) )
    }
    $( '#' + ingID ).prop( 'checked', true )
  }


  //
  // Over-ride Anchor Linking
  //

  // Identify and scroll to the linked recipe
  var anchor = parseURL( window.location.href ).tag
  console.log( 'Scrolling to anchor: ' + anchor )
  if ( anchor.length > 0 ) {
    console.log( 'Scrolling!' )
    document.getElementById( anchor ).scrollIntoView( {behavior: 'smooth', block: 'start'} )
  }
  // Over-ride internal HTML linking from <a> tags
  $( 'a' ).on( 'click', ( event ) => {
    var tag = event.target.hash.replace( '#', '' )  // or use <str>.slice(1);
    // // If the id is for the cody house panel, ignore (e.g. cd-nav, cd-.*, etc.)
    // if (tag.indexOf('cd-') != 0) {
    // Only use for recipe links
    if ( tag.indexOf( 'recipe-' ) === 0 ) {
      event.preventDefault()
      var comps = parseURL( window.location.href )
      var finalUrl = comps.baseUrl + comps.ingBR + comps.ingredients.join( ',' ) +
                     comps.tagBR + tag.replace( ' ', '_' )
      console.log( 'Scrolling to new tag: ' + tag + ' for finalUrl: ' + finalUrl )
      document.getElementById( tag ).scrollIntoView( {behavior: 'smooth', block: 'start'} )
      window.history.pushState( null, null, finalUrl )
    }
  } )
} )