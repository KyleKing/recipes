'use strict'

import Recipe from './Recipe.js'

/*
>> Create Table of Contents, Headers, and Recipes
 */


// Add Table of Contents to HTMl
const addToC = function( contentDivID ) {
  // Create header for ToC
  const trgt = document.getElementById( contentDivID )
  crel( trgt, crel( 'h3', {'id': 'toc'}, 'Recipes Table of Contents' ) )

  // Unwrap the toc object into a single list of recipe titles
  let allRcps = []
  for ( let group of Object.keys( localDB.toc ) )
    allRcps = [...allRcps, ...localDB.toc[group]]

  // Use the recipe title index in allRcps to get the full recipe index in localDB
  const getRcpByName = function( rcpTtl ) {
    return localDB.recipes[allRcps.indexOf( rcpTtl )]
  }

  // Add link for each recipe per group/heading
  for ( let group of Object.keys( localDB.toc ) ) {
    const titles = []
    for ( let rcpTtl of localDB.toc[group] )
      titles.push( crel( 'li', crel( 'a', {'href': `#${getRcpByName( rcpTtl ).id}`}, rcpTtl ) ) )
    crel( trgt, crel( 'ul', crel( 'li',
      crel( 'a', {'href': `#${group}`}, group ),
      crel( 'ul', titles )
    ) ) )
  }
  // Add last link to Footer
  crel( trgt, crel( 'ul', crel( 'li', crel( 'a', {'href': '#footer'}, 'Footer' ) ) ) )
}


// Recipe initializer
const updateRecipes = function( recipes ) {
  const contentDivID = 'crel-content'
  // Tear down last recipe container
  const el = document.getElementById( contentDivID )
  if ( el )
    el.remove()
  // Initialize new content container
  crel( document.getElementById( 'crel-target' ), crel( 'div', {'id': contentDivID} ) )

  // Parse input as either raw local database or filtered matches from Fuse
  let isFuseSearch = false
  if ( recipes.length > 0 )
    isFuseSearch = 'item' in recipes[0] && 'matches' in recipes[0]
  else
    crel( document.getElementById( contentDivID ), crel( 'h1', 'No Matches Found' ) )

  // Add table of contents if no Fuse filtering
  if ( recipes.length > 0 && !isFuseSearch )
    addToC( contentDivID )

  // Create recipes
  for ( let recipe of recipes )
    new Recipe( isFuseSearch, contentDivID, recipe )
}


// Wrapper for searching database
const search = function( searchPhrase ) {
  // Set options to be strict and limit fuzziness of search
  const options = {
    distance: 10000,
    includeMatches: true,
    keys: localDB.searchKeys,
    location: 0,
    maxPatternLength: 32,
    minMatchCharLength: searchPhrase.length - 1,
    shouldSort: true,
    threshold: 0.1,
  }
  // Search database with Fuse
  const fuse = new Fuse( localDB.recipes, options )
  const fuseResults = fuse.search( searchPhrase )
  // Add matched recipes to view
  updateRecipes( fuseResults )
}


// Initialize application
const init = function() {
  updateRecipes( localDB.recipes )
}


/*
>> Slide in Side Navigation inspired by CodyHouse article:
 */

jQuery( document ).ready( ( $ ) => {
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
} )


/*
>> Manipulate URL
 */


// Workaround limitations of tag to store object for saved state
function parseURL( fullUrl ) {
  const br = '\?'
  // Initialize URL components for export
  const urlComps = {
    'ingBR': `${br}ingredients`,
    'ingredients': [],
    'tag': '',
    'tagBR': `${br}tag=`,
  }
  // Separate ingredient list from rest of URL
  const components = fullUrl.split( br )
  for ( let idx = 0; idx < components.length; idx ++ ) {
    const comp = '?' + components[idx]
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

const registerIngredientClick = function() {
  // Catch click event for ingredient
  $( '.ingredient' ).on( 'click', ( event ) => {
    // For debugging:
    const fullUrl = window.location.href
    console.log( 'Current url: ' + fullUrl )
    // console.log(event);
    // console.log(event.target.classList);

    // Either add or remove ingredient ID and set check box value appropriately
    const comps = parseURL( fullUrl )
    const ingID = $( event.target ).attr( 'id' )
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
    const finalUrl = comps.baseUrl + comps.ingBR + comps.ingredients.join( ',' ) +
                     comps.tagBR + comps.tag
    window.history.pushState( null, null, finalUrl )
    console.log( 'Final url: ' + finalUrl + '\n' )
  } )

  // TODO: Implement only for 'Make' mode:
  // // Read ingredients state and update check boxes:
  // const fullUrl = window.location.href
  // const ingredients = parseURL( fullUrl ).ingredients
  // for ( let idx = 0; idx < ingredients.length; idx++ ) {
  //   const ingID  = ingredients[idx]
  //   if ( fullUrl.search( 'file:/' ) ) {
  //     console.log( 'Toggling? #' + ingID )
  //     console.log( $( '#' + ingID ) )
  //   }
  //   $( '#' + ingID ).prop( 'checked', true )
  // }
}


// Override Anchor Linking from ToC
const registerSmoothScroll = function() {
  // TODO: trigger smooth scroll from completion of Crel HTML generation
  // // Identify and scroll to the linked recipe
  // const anchor = parseURL( window.location.href ).tag
  // if ( anchor.length > 0 )
  //   document.getElementById( anchor ).scrollIntoView( {behavior: 'smooth', block: 'start'} )

  // Override internal HTML linking from <a> tags
  $( 'a' ).on( 'click', ( event ) => {
    const tag = event.target.hash.replace( '#', '' )  // or use <str>.slice(1);
    // Ignore links from CodyHouse Panel and Section Headers. Only apply to Recipes
    if ( tag.indexOf( 'recipe-' ) === 0 ) {
      event.preventDefault()
      const comps = parseURL( window.location.href )
      const finalUrl = comps.baseUrl + comps.ingBR + comps.ingredients.join( ',' ) +
                       comps.tagBR + tag.replace( ' ', '_' )
      document.getElementById( tag ).scrollIntoView( {behavior: 'smooth', block: 'start'} )
      window.history.pushState( null, null, finalUrl )
    }
  } )
}


/*
>> Handle Application Load and Events
 */


// Add event detection for search
const nodeInputSearch = document.getElementById( 'search-input' )
nodeInputSearch.addEventListener( 'keyup', ( event ) => {
  // Either load all recipes or apply search phrase from input
  if ( event.key === 'Enter' ) {
    if ( nodeInputSearch.value.length === 0 )
      init()
    else
      search( nodeInputSearch.value )
  }
} )


// On ready, initialize application
window.onload = function() {
  init()
  $( 'footer' ).removeClass( 'hide-while-loading' )
  registerSmoothScroll()
  registerIngredientClick()
}
