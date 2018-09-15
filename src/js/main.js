'use strict'

import {initContent, searchRecipes} from './Content.js'
import RegisterScroll from './RegisterScroll.js'

// Initialize the Lazy Image Loader
var myLazyLoad = new LazyLoad( {
  'elements_selector': '.lazy',
} )

// Initialize event detection for key entry in search bar
const nodeInputSearch = document.getElementById( 'search-input' )
nodeInputSearch.addEventListener( 'keyup', ( ) => {
  // Either load all recipes or apply search phrase from input
  if ( nodeInputSearch.value.length === 0 )
    initContent()
  else
    // TODO: add search to URL?
    searchRecipes( nodeInputSearch.value )
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
  initContent()
  $( 'footer' ).removeClass( 'hide-while-loading' )
  // registerIngredientClick()    // TODO: Disabled for now - use in 'Make' mode
  RegisterScroll()
  myLazyLoad.update()
}
