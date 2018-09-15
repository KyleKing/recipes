'use strict'

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
      scrollTo( document.getElementById( tag ) )

      // TODO: Add recipe linking to URL
      // const comps = parseURL( window.location.href )
      // const finalUrl = comps.baseUrl + comps.ingBR + comps.ingredients.join( ',' ) +
      //                  comps.tagBR + tag.replace( ' ', '_' )
      // window.history.pushState( null, null, finalUrl )
    }
  } )
}
