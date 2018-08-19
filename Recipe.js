'use strict'

import Highlighter from './Highlighter.js'

// Default Recipe class
export default class {

  constructor ( isFuseSearch, contentDivID, rcp ) {
    this.contentDivID = contentDivID
    this.isFuseSearch = isFuseSearch
    this.hltr = new Highlighter()
    this.parseMatches( rcp )
  }

  parseMatches ( rcp ) {
    // Initialize lookup dictionary
    let matchLookup = {}
    if ( this.isFuseSearch ) {
      matchLookup = this.hltr.unwrapHighlights( rcp.matches )
      rcp = rcp.item
    }

    // Identify matching regions in title, if any
    let titleMatches = []
    if ( 'title' in matchLookup )
      titleMatches = matchLookup.title['0']
    // Add link to recipe source, if one exists
    let sourceLink = crel( 'span', '' )
    if ( rcp.source.indexOf( 'http' )  >= 0 )
      sourceLink = crel( 'a', {'href': rcp.source}, crel( 'i', '(Source)' ) )
    // Cleanup notes section, if any
    let additionalNotes = crel( 'span', '' )
    if ( rcp.notes.length > 0 ) {
      additionalNotes = crel( 'div',
        crel( 'p', 'Notes:' ),
        crel( 'ul', this.createList( rcp, 'notes', matchLookup ) )
      )
    }

    this.insertRecipe( rcp, titleMatches, sourceLink, additionalNotes, matchLookup )
  }

  // Generic generator of HTML-list elements based on recipe and key argument
  createList ( rcp, key, matchLookup = {} ) {
    const items = []
    if ( key in rcp ) {
      for ( let idx = 0; idx < rcp[key].length; idx++ ) {
        let item = rcp[key][idx]
        item = this.hltr.highlightItem( item, key, idx, matchLookup )
        items.push( crel( 'li', item ) )
      }
    }
    return items
  }

  // Generate HTML for each recipe
  insertRecipe ( rcp, titleMatches, sourceLink, additionalNotes, matchLookup = {} ) {
    const group = rcp.group
    // See if section title is needed
    if ( !this.isFuseSearch && localDB.toc[group].indexOf( rcp.title ) === 0 ) {
      crel( document.getElementById( this.contentDivID ),
        crel( 'h1', {'id': group}, group )
      )
    }

    // Create HTML for each recipe (title, image, ingredients, instructions)
    crel( document.getElementById( this.contentDivID ),
      crel( 'div', {'class': 'row br'},
        // Add Recipe title and link to source, if any
        crel( 'h5', {'class': 'twelve columns', 'id': rcp.id},
          crel( 'a',
            {'class': 'unstyled', 'href': `#${rcp.id}`, 'id': `${rcp.id}`},
            this.hltr.highlightText( rcp.title, titleMatches )
          ),
          crel( 'span', ' ' ),
          sourceLink
        )
      ),
      crel( 'div', {'class': 'row'},
        // Add the reference image
        crel( 'img', {'alt': rcp.id, 'class': 'five columns', 'src': rcp.imgSrc} ),
        // Add ingredients and recipe
        crel( 'div', {'class': 'seven columns', 'id': rcp.id},
          this.constCreateListGroup( rcp, matchLookup ),
          crel( 'ol',
            this.createList( rcp, 'recipe', matchLookup )
          ),
          additionalNotes
        )
      )
    )
  }

  // Create list of HTML elements for ingredients with interactive check box
  createCheckedItems ( rcpID, header, list, matchObj = {} ) {
    const ingredients = []
    for ( let idx = 1; idx < list.length; idx++ ) {
    // Highlight matched text, if any
      list[idx] = this.hltr.highlightItem( list[idx], `ingredients.${header}`, idx, matchObj )
      // Add input (checkbox) then matched label with unique ID linking both
      const uniqID = `${rcpID}-${header.toLowerCase().replace( /\s+/g, '_' )}-${idx}`
      ingredients.push( crel( 'input', {
        'class': 'ingredient magic-checkbox',
        'id': uniqID,
        'name': 'layout',
        'type': 'checkbox',
      } ) )
      ingredients.push( crel( 'label', {'for': uniqID}, list[idx] ) )
    }
    return ingredients
  }

  // Create unordered list beneath paragraph header
  constCreateListGroup ( rcp, matchObj = {} ) {
    let ingredientList = []
    for ( let header of Object.keys( rcp.ingredients ) ) {
      // Highlight section header if match made
      //  FYI: header is the first value in the array, so Fuse will index the text
      let customHeader = rcp.ingredients[header][0]
      customHeader = this.hltr.highlightItem( customHeader, `ingredients.${header}`, 0, matchObj )
      // Create ingredient section header and checkable items
      ingredientList.push( crel( 'p',  customHeader ) )
      ingredientList.push( crel( 'ul',
        this.createCheckedItems( rcp.id, header, rcp.ingredients[header], matchObj )
      ) )
    }
    return ingredientList
  }
}
