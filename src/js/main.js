'use strict'

import {initContent, searchRecipes} from './Content.js'
import {registerURLHandler, updateSearch} from './URL.js'
import RegisterScroll from './RegisterScroll.js'

// Initialize the Lazy Image Loader
var myLazyLoad = new LazyLoad( {
  'elements_selector': '.lazy',
} )

const applySearchInput = function( val ) {
  if ( val.length === 0 )
    initContent()
  else {
    // If too many values, treat whole string as search
    let vals = val.split( ':' )
    if ( vals.length > 2  )
      vals = [val]
    // Use the first, ':' input for typical plain text search
    if ( val[0] !== ':' ) {
      updateSearch( val ) // add search phrase to URL
      searchRecipes( vals[0] )
    } else
      vals = ['', val.slice( 1 )]

    // If second argument, apply star filter
    if ( vals.length === 2 && vals[1].length > 0 ) {
      const ratings = vals[1].split( '' ).map( rating => `rating-${rating}` )
      document.querySelectorAll( '.rated-row' ).forEach( ( el ) => {
        if ( ratings.indexOf( el.classList[1] ) !== -1 )
          el.classList.remove( 'hide' )
        else
          el.classList.add( 'hide' )
      } )
    }
  }
}

// Initialize event detection for key entry in search bar
const nodeInputSearch = document.getElementById( 'search-input' )
nodeInputSearch.addEventListener( 'keyup', ( ) => {
  // Either load all recipes or apply search phrase from input
  applySearchInput( nodeInputSearch.value )
  // Update lazy loading after DOM changes
  myLazyLoad.update()
} )

// Register CTRL + F keyboard shortcut to select search bar
document.addEventListener( 'keydown', ( event ) => {
  if ( event.ctrlKey && event.code === 'KeyF' ) {
    event.preventDefault()
    const input = document.getElementById( 'search-input' )
    input.focus()
    input.setSelectionRange( 0, input.value.length )
  }
} )

// On ready, initialize application
window.onload = function() {
  registerURLHandler( nodeInputSearch, initContent, applySearchInput )
  $( 'footer' ).removeClass( 'hide-while-loading' )
  // registerIngredientClick()    // FYI: Disabled for now - use in 'Make' mode
  RegisterScroll()
  myLazyLoad.update()
}
