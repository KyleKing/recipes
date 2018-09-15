'use strict'

/*
>> Manipulate URL
 */

// Workaround limitations of tag to store object for saved state
export function parseURL( fullUrl ) {
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
