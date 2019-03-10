'use strict'

// Return the full element height including margin
// Docs: https://plainjs.com/javascript/styles/getting-width-and-height-of-an-element-23/
const elHeight = function( el ) {
  const style = window.getComputedStyle ? getComputedStyle( el, null ) : el.currentStyle
  const marginTop = parseInt( style.marginTop ) || 0
  const marginBottom = parseInt( style.marginBottom ) || 0
  return el.offsetHeight + marginTop + marginBottom
}

// Wrapper for scroll with calculated offset for height of the search bar
export default function( el, nav = document.getElementById( 'search-input' ) ) {
  console.log( el )
  if ( el != null ) {
    const scrollPos = el.getBoundingClientRect().top
    const navOffset = elHeight( nav ) + 15
    window.scrollBy( 0, Math.round( scrollPos - navOffset ) )
  }
}
