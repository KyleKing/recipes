'use strict'

import {initContent, searchRecipes} from './Content.js'
import {registerURLHandler, updateSearch} from './URL.js'
import RegisterScroll from './RegisterScroll.js'

// Initialize the Lazy Image Loader
var myLazyLoad = new LazyLoad( {
  'elements_selector': '.lazy',
} )

// Initialize event detection for key entry in search bar
const nodeInputSearch = document.getElementById( 'search-input' )
nodeInputSearch.addEventListener( 'keyup', ( ) => {
  // Either load all recipes or apply search phrase from input
  const val = nodeInputSearch.value
  if ( val.length === 0 )
    initContent()
  else if ( val[0] === ':' ) {
    // Note: this keeps search state. Could search crab, then type :23 to filter
    if ( val.length > 1 ) {
      const ratings = val.slice( 1 ).split( '' ).map( rating => `rating-${rating}` )
      document.querySelectorAll( '.rating-row' ).forEach( ( el ) => {
        if ( ratings.indexOf( el.classList[1] ) !== -1 )
          el.classList.remove( 'hide' )
        else
          el.classList.add( 'hide' )
      } )
    }
  } else {
    updateSearch( val ) // add search phrase to URL
    searchRecipes( val )
  }
  // Update lazy loading after DOM changes
  myLazyLoad.update()
} )

// Hijack CTRL/Meta + F keyboard shortcut to select search bar
document.addEventListener( 'keydown', ( event ) => {
  if ( ( event.metaKey || event.ctrlKey ) && event.code === 'KeyF' ) {
    event.preventDefault()
    const input = document.getElementById( 'search-input' )
    input.focus()
    input.setSelectionRange( 0, input.value.length )
  }
} )

// On ready, initialize application
window.onload = function() {
  registerURLHandler( nodeInputSearch, initContent, searchRecipes )
  $( 'footer' ).removeClass( 'hide-while-loading' )
  // registerIngredientClick()    // FYI: Disabled for now - use in 'Make' mode
  RegisterScroll()
  myLazyLoad.update()
}
