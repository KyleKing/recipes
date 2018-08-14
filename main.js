/*
>> Highlight Text Matched with Fuse
 */

/**
 * Wrap matched regions in given string with the highlight CSS class
 *   Based on: https://github.com/krisk/Fuse/issues/6#issuecomment-352192752
 *   FYI: does not account for overlapping highlighted regions, if that's even possible...
 * @param  {String} text    Text matched with Fuse
 * @param  {Array} regions  Array of arrays with match indexes in [start, stop]
 * @return {Array}          Crel HTML elements
 */
function highlightText( text, regions ) {
  if( !regions ) return text
  let nextStartIdx = 0
  const content = []
  regions.forEach( ( region ) => {
    // Add the section between (last match || start) to start of next match
    content.push( crel( 'span', text.substring( nextStartIdx, region[0] ) ) )
    // Add highlighted section
    content.push( crel( 'span', {'class': 'highlight'}, text.substring( region[0], region[1] + 1 ) ) )
    nextStartIdx = region[1] + 1
  } )
  // Add final section after last match
  content.push( crel( 'span', text.substring( nextStartIdx ) ) )
  return content
}

/**
 * Check for a match in lookup object key and index, then pass to highlight function
 * @param  {String} item      Raw string
 * @param  {String} key       Database key in dot syntax for matchObj
 * @param  {Int} idx          Index of item
 * @param  {Object} matchObj  Match lookup Object
 * @return {String || Array}  Crel HTML elements or original, raw string
 */
const highlightItem = function( item, key, idx, matchObj ) {
  if ( key in matchObj && matchObj[key].arrayIndices.indexOf( idx ) !== -1 )
    return( highlightText( item, matchObj[key][String( idx )] ) )
  return( item )
}

/**
 * Take matches object and create lookup to more efficiently highlight matches in text
 * @param  {Object} fuseMatches Subset of local database matched with Fuse
 * @return {Object}             Optimize object structure to simplify highlighting
 */
const unwrapHighlights = function( fuseMatches ) {
  let matchLookup = {}
  for ( let match of fuseMatches ) {
    // Initialize match object with list of all arrays matched
    if ( !( String( match.key ) in matchLookup ) )
      matchLookup[match.key] = {'arrayIndices': []}
    // Store match information
    matchLookup[match.key].arrayIndices.push( match.arrayIndex )
    matchLookup[match.key][String( match.arrayIndex )] = match.indices
  }
  return matchLookup
}

/*
>> Create HTML Content with Crel
 */

/**
 * Create list of HTML elements for ingredients with interactive check box
 * @param  {String} header   Key for ingredients
 * @param  {Array} list      List of all ingredients
 * @param  {Object} matchObj Optional match lookup object for highlighting
 * @return {Array}           Crel HTML elements
 */
const createCheckedItems = function( header, list, matchObj = {} ) {
  const ingredients = []
  for ( let idx = 1; idx < list.length; idx++ ) {
    // Highlight matched text, if any
    list[idx] = highlightItem( list[idx], `ingredients.${header}`, idx, matchObj )
    // Add input (checkbox) then matched label with unique ID linking both
    const uniqID = `${header.toLowerCase().replace( /\s+/g, '_' )}-${idx}`
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

/**
 * Create unordered list beneath paragraph header
 * @param  {Object} rcp      Local database entry from original JSON file
 * @param  {Object} matchObj Match lookup object for highlighting
 * @return {Array}           Crel HTML elements
 */
const constCreateListGroup = function( rcp, matchObj = {} ) {
  let ingredientList = []
  for ( let header of Object.keys( rcp.ingredients ) ) {
    // Highlight section header if match made
    //  FYI: header is duplicated from key to first index of array for this purpose
    let customHeader = rcp.ingredients[header][0]
    customHeader = highlightItem( customHeader, `ingredients.${header}`, 0, matchObj )
    // Create ingredient section header and checkable items
    ingredientList.push( crel( 'p',  customHeader ) )
    ingredientList.push( crel( 'ul',
      createCheckedItems( header, rcp.ingredients[header], matchObj )
    ) )
  }
  return ingredientList
}

/**
 * Generic generator of HTML-list elements based on recipe and key argument
 * @param  {Object} rcp         Local database entry from original JSON file
 * @param  {String} key         Key for item in recipe
 * @param  {Object} matchLookup Optional match lookup object for highlighting
 * @return {Array}              Crel HTML elements
 */
const createList = function( rcp, key, matchLookup = {} ) {
  const items = []
  if ( key in rcp ) {
    for ( let idx = 0; idx < rcp[key].length; idx++ ) {
      let item = rcp[key][idx]
      item = highlightItem( item, key, idx, matchLookup )
      items.push( crel( 'li', item ) )
    }
  }
  return items
}

/**
 * Recipe initializer
 * @param  {Object} recipes Fuse match with keys 'item' and 'matches'
 * @return {None}           Creates HTML elements in DOM
 */
const updateRecipes = function( recipes ) {
  // Delete last recipe container to repopulate recipes
  const el = document.getElementById( 'crel-content' )
  if ( el )
    el.remove()

  // Create new container and iterate over recipes
  for ( let recipe of recipes ) {

    const rcp = recipe.item
    const matchLookup = unwrapHighlights( recipe.matches )

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
        crel( 'ul', createList( rcp, 'notes', matchLookup ) )
      )
    }

    // Generate HTML
    crel( document.getElementById( 'crel-target' ),
      crel( 'div', {'class': 'row br'},
        // Add Recipe title and link to source, if any
        crel( 'h5', {'class': 'twelve columns', 'id': rcp.id},
          crel( 'a',
            {'class': 'unstyled', 'href': `#${rcp.id}`, 'id': `${rcp.id}`},
            highlightText( rcp.title, titleMatches )
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
          constCreateListGroup( rcp, matchLookup ),
          crel( 'ol',
            createList( rcp, 'recipe', matchLookup )
          ),
          additionalNotes
        )
      )
    )
  }

}

/*
>> Search local recipe database
 */

/**
 * Wrapper for searching database
 * @param  {String} searchPhrase Search Phrase entered in search input
 * @return {None}                Updates HTML content with matched elements
 */
const search = function( searchPhrase ) {
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
  const fuse = new Fuse( localDB.recipes, options )
  const fuseResults = fuse.search( searchPhrase )

  console.log( 'fuseResults:' )
  console.log( fuseResults )

  // Add matched recipes to view
  updateRecipes( fuseResults )
}

// TODO: Add text input and button event click to update search results
search( 'KriSPie' )


