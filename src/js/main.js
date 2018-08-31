'use strict'

import Recipe from './Recipe.js'

// Initialize the Lazy Image Loader
var myLazyLoad = new LazyLoad( {
  'elements_selector': '.lazy',
} )

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

// const registerIngredientClick = function() {
//   // Catch click event for ingredient
//   $( '.ingredient' ).on( 'click', ( event ) => {
//     // For debugging:
//     const fullUrl = window.location.href
//     console.log( 'Current url: ' + fullUrl )
//     // console.log(event)
//     // console.log(event.target.classList)

//     // Either add or remove ingredient ID and set check box value appropriately
//     const comps = parseURL( fullUrl )
//     const ingID = $( event.target ).attr( 'id' )
//     if ( event.currentTarget.checked ) {
//       if ( comps.ingredients.length === 0 )
//         comps.ingredients = [ingID]
//       else
//         comps.ingredients.push( ingID )

//     } else {
//       // console.log('idx:');
//       // console.log(ingID);
//       // console.log(comps.ingredients);
//       // console.log(comps.ingredients.indexOf(ingID));
//       comps.ingredients.splice( comps.ingredients.indexOf( ingID ), 1 )
//     }
//     comps.ingredients.sort()
//     const finalUrl = comps.baseUrl + comps.ingBR + comps.ingredients.join( ',' ) +
//                      comps.tagBR + comps.tag
//     window.history.pushState( null, null, finalUrl )
//     console.log( 'Final url: ' + finalUrl + '\n' )
//   } )

//   // TODO: Implement only for 'Make' mode:
//   // // Read ingredients state and update check boxes:
//   // const fullUrl = window.location.href
//   // const ingredients = parseURL( fullUrl ).ingredients
//   // for ( let idx = 0; idx < ingredients.length; idx++ ) {
//   //   const ingID  = ingredients[idx]
//   //   if ( fullUrl.search( 'file:/' ) ) {
//   //     console.log( 'Toggling? #' + ingID )
//   //     console.log( $( '#' + ingID ) )
//   //   }
//   //   $( '#' + ingID ).prop( 'checked', true )
//   // }
// }


/*
>> Handle Scroll Events
 */



// Based on: https://stackoverflow.com/a/18660968/3219667
function isLinkInternal( link ) {
  var tmp = document.createElement( 'a' )
  tmp.href = link
  return tmp.host === window.location.host
}

// Return the full element height including margin
// Docs: https://plainjs.com/javascript/styles/getting-width-and-height-of-an-element-23/
const elHeight = function( el ) {
  const style = window.getComputedStyle ? getComputedStyle( el, null ) : el.currentStyle
  const marginTop = parseInt( style.marginTop ) || 0
  const marginBottom = parseInt( style.marginBottom ) || 0
  return el.offsetHeight + marginTop + marginBottom
}

// Wrapper for scroll with calculated offset for height of the search bar
const scrollTo = function( el, nav = document.getElementById( 'search-input' ) ) {
  const scrollPos = el.getBoundingClientRect().top
  const navOffset = elHeight( nav ) + 5
  window.scrollBy( 0, Math.round( scrollPos - navOffset ) )
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
    // Only apply to internal links
    // console.log( event.currentTarget )
    if( isLinkInternal( event.currentTarget.href ) ) {
      event.preventDefault()
      const tag = event.currentTarget.hash.replace( '#', '' )  // or use <str>.slice(1);
      scrollTo( document.getElementById( tag ) )

      // TODO: Add recipe linking to URL
      // const comps = parseURL( window.location.href )
      // const finalUrl = comps.baseUrl + comps.ingBR + comps.ingredients.join( ',' ) +
      //                  comps.tagBR + tag.replace( ' ', '_' )
      // window.history.pushState( null, null, finalUrl )
    }
  } )
}

// Update scroll progress bar on scroll
window.addEventListener( 'scroll', () => {
  const winheight = $( document ).height()
  const wintop = $( document ).scrollTop()
  const totalScroll = ( wintop / winheight ) * 100
  // console.log( `total scroll: ${totalScroll} | winheight: ${winheight} | with wintop: ${wintop}` )
  $( '.progressBar' ).css( 'width', totalScroll + '%' )
} )


/*
>> Handle Application Load and Events
 */


// Add event detection of enter key when typing in search bar
const nodeInputSearch = document.getElementById( 'search-input' )
nodeInputSearch.addEventListener( 'keyup', ( ) => {
  // Either load all recipes or apply search phrase from input
  if ( nodeInputSearch.value.length === 0 )
    init()
  else
    // TODO: add search to URL?
    search( nodeInputSearch.value )
  // Update lazy loading after DOM changes
  myLazyLoad.update()
} )

// Use Meta + F to select input search bar
document.addEventListener( 'keydown', ( event ) => {
  // console.log( event.code )
  if ( ( event.metaKey || event.ctrlKey ) && event.code === 'KeyF' ) {
    event.preventDefault()
    const input = document.getElementById( 'search-input' )
    input.focus()
    input.setSelectionRange( 0, input.value.length )
  }
} )

// On ready, initialize application
window.onload = function() {
  init()
  $( 'footer' ).removeClass( 'hide-while-loading' )
  // TODO: Disabled for now - use in 'Make' mode
  // registerIngredientClick()
  registerSmoothScroll()
  // Update lazy loading after DOM creation
  myLazyLoad.update()
}
