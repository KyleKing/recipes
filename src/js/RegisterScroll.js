'use strict'

import ScrollTo from './ScrollTo.js'
import {updateRecipe} from './URL.js'

/*
>> Handle Scroll Events
 */

// Based on: https://stackoverflow.com/a/18660968/3219667
function isLinkInternal( link ) {
  var tmp = document.createElement( 'a' )
  tmp.href = link
  return tmp.host === window.location.host
}

// Override Anchor Linking from ToC
export default function() {
  // On scroll, update the progress bar
  window.addEventListener( 'scroll', () => {
    const scrollableDocHeight = $( document ).height() - $( window ).height()
    const scrollPos = $( document ).scrollTop()
    const totalScroll = ( scrollPos / scrollableDocHeight ) * 100
    // console.log( `total: ${totalScroll} = scrollPos: ${scrollPos} / sdh: ${scrollableDocHeight}` )
    $( '.progressBar' ).css( 'width', totalScroll + '%' )
  } )

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
      ScrollTo( document.getElementById( tag ) )
      updateRecipe( tag ) // Update URL
    }
  } )
}
