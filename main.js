'use strict'

import Recipe from './Recipe.js'

/*
>> Create Table of Contents, Headers, and Recipes
 */

// Add Table of Contents to HTMl
const addToC = function( contentDivID ) {
  // Create header for ToC
  const trgt = document.getElementById( contentDivID )
  crel( trgt, crel( 'h3', {'id': 'toc', 'style': 'padding-top: 50px'}, 'Recipes Table of Contents' ) )

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
  // // Search database with Fuse
  // const fuse = new Fuse( localDB.recipes, options )
  // const fuseResults = fuse.search( searchPhrase )
  // // Add matched recipes to view
  // updateRecipes( fuseResults )
}

// Initialize application
const init = function() {
  updateRecipes( localDB.recipes )
}

// Add event detection for search
const node = document.getElementById( 'search-input' )
node.addEventListener( 'keyup', ( event ) => {
  // Either load all recipes or apply search phrase from input
  if ( event.key === 'Enter' ) {
    if ( node.value.length === 0 )
      init()
    else
      search( node.value )
  }
} )

// On ready, initialize application
window.onload = function() {
  init()
}
