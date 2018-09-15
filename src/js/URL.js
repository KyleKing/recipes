'use strict'

/*
>> Manipulate URL
 */

const check = function( comp, br ) {
  return( comp.indexOf( br ) >= 0 )
}

const getArg = function( comp, br ) {
  return( comp.split( br )[1] )
}

// Workaround limitations of tag to store object for saved state
export function parseURL( fullUrl ) {
  // console.log( 'Crrnt URL: ' + fullUrl )
  const br = '\?'
  // Initialize URL components for export
  const urlComps = {
    'ingBR': `${br}ing=`,
    'ingredients': [],
    'other': '',
    'search': '',
    'searchBR': `${br}search=`,
    'tag': '',
    'tagBR': `${br}tag=`,
  }
  // Separate ingredient list from rest of URL
  for ( let comp of fullUrl.split( br ) ) {
    comp = `?${comp}`

    if ( check( comp, urlComps.ingB ) )
      urlComps.ingredients = getArg( comp, urlComps.ingBR ).split( ',' )
    else if ( check( comp, urlComps.searchBR ) )
      urlComps.search = getArg( comp, urlComps.searchBR )
    else if ( check( comp, urlComps.tagBR ) )
      urlComps.tag = getArg( comp, urlComps.tagBR )
    else if ( comp.indexOf( 'http' ) >= 0 )
      urlComps.baseUrl = comp.slice( 1 ).split( '#' )[0]
    else
      urlComps.other += comp.split( '#' )[0]

  }
  return( urlComps )
}

// Workaround limitations of tag to store object for saved state
export function formAndPushURL( comps ) {
  comps.ingredients.sort()

  let finalUrl = comps.baseUrl + comps.other + '#'
  if ( comps.search.length > 0 )
    finalUrl += comps.searchBR + comps.search
  if ( comps.tag.length > 0 )
    finalUrl += comps.tagBR + comps.tag
  if ( comps.ingredients.length > 0 )
    finalUrl += comps.ingBR + comps.ingredients.join( ',' )

  // console.log( 'Final URL: ' + finalUrl )
  window.history.pushState( null, null, finalUrl )
  return( finalUrl )
}

// // TODO: Implement only for 'Make' mode:
// const registerIngredientClick = function() {
//   // Catch click event for ingredient
//   $( '.ingredient' ).on( 'click', ( event ) => {
//     // Either add or remove ingredient ID and set check box value appropriately
//     const comps = parseURL( window.location.href )
//     const ingID = $( event.target ).attr( 'id' )
//     if ( event.currentTarget.checked ) {
//       if ( comps.ingredients.length === 0 )
//         comps.ingredients = [ingID]
//       else
//         comps.ingredients.push( ingID )
//     } else {
//       // console.log('idx:')
//       // console.log(ingID)
//       // console.log(comps.ingredients)
//       // console.log(comps.ingredients.indexOf(ingID))
//       comps.ingredients.splice( comps.ingredients.indexOf( ingID ), 1 )
//     }
//     formAndPushURL( comps )
//   } )

//   // // Read ingredients state and update check boxes:
//   // const fullUrl = window.location.href
//   // const ingredients = parseURL( fullUrl ).ingredients
//   // for ( let idx = 0 idx < ingredients.length idx++ ) {
//   //   const ingID  = ingredients[idx]
//   //   if ( fullUrl.search( 'file:/' ) ) {
//   //     console.log( 'Toggling? #' + ingID )
//   //     console.log( $( '#' + ingID ) )
//   //   }
//   //   $( '#' + ingID ).prop( 'checked', true )
//   // }
// }

export function updateSearch( phrase ) {
  const comps = parseURL( window.location.href )
  comps.search = encodeURIComponent( phrase.trim() )
  formAndPushURL( comps )
}

// Use the URL to initialize the application
export function RegisterURLHandler( input, init, search ) {
  const comps = parseURL( window.location.href )
  if ( comps.search.length > 0 ) {
    input.value = decodeURI( comps.search )
    search( comps.search )
  } else {
    // Check if recipe is linked, then create scroll to event on timeout
    init()
  }
}
