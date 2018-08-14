//
// Highlight regions matched by Fuse
// https://github.com/krisk/Fuse/issues/6#issuecomment-352192752
//

// FYI: does not account for overlapping highlighted regions, if that's even possible...
function highlightText( text, regions ) {
  if( !regions ) return text

  const content = []
  let nextStartIdx = 0
  regions.forEach( ( region ) => {
    content.push( crel( 'span', text.substring( nextStartIdx, region[0] ) ) )
    content.push( crel( 'span', {'class': 'highlight'}, text.substring( region[0], region[1] + 1 ) ) )
    nextStartIdx = region[1] + 1
  } )
  content.push( crel( 'span', text.substring( nextStartIdx ) ) )
  return content
}

//
// Create HTML with Crel
//

// Take matches object and create lookup to more efficiently highlight matches in text
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

// Create list of HTML elements for ingredients with interactive checkbox
const createCheckedItems = function( rcpID, header, list, matches = {'arrayIndices': []} ) {
  const ingredients = []
  for ( let idx = 0; idx < list.length; idx++ ) {
    const uniqID = `${rcpID}-${header.toLowerCase().replace( /\s+/g, '_' )}-${idx}`
    let ingredient = list[idx]
    if ( matches.arrayIndices.indexOf( idx ) !== -1 )
      ingredient = highlightText( ingredient, matches[String( idx )] )
    ingredients.push( crel( 'input',
      {
        'class': 'ingredient magic-checkbox',
        'id': uniqID,
        'name': 'layout',
        'type': 'checkbox',
      } ) )
    ingredients.push( crel( 'label', {'for': uniqID}, ingredient ) )
  }
  return ingredients
}

// Create unordered list beneath paragraph header
const constCreateListGroup = function( rcp, matchLookup = {} ) {
  let ingredientList = []
  for ( let header of Object.keys( rcp.ingredients ) ) {
    const ulArgs = [rcp.id, header, rcp.ingredients[header]]
    // Identify if matches were found in this section
    const matchKey = `ingredients.${header}`
    if ( matchKey in matchLookup )
      ulArgs.push( matchLookup[matchKey] )
    // Create ingredient section title and checkable items
    ingredientList.push( crel( 'p', header.toUpperCase() ) )
    ingredientList.push( crel( 'ul',
      createCheckedItems( ...ulArgs )
    ) )
  }
  return ingredientList
}

// // All keys should have known hierarchy
// const splitDot = function( key, obj ) {
//   const keys = key.split( '.' )
//   for ( let idx = 0; idx < keys.length; idx++ ) {
//     if ( keys[idx] in obj ) {
//       obj = obj[keys[idx]]
//       if ( idx === keys.length )
//         return obj
//     }
//   }
//   return {}
// }

// Create HTML-list elements based on recipe and key argument
const createList = function( recipe, key, matchLookup = {} ) {
  let matches = {'arrayIndices': []}
  if ( key in matchLookup )
    matches = matchLookup[key]
  const items = []
  if ( key in recipe ) {
    for ( let idx = 0; idx < recipe[key].length; idx++ ) {
      let item = recipe[key][idx]
      if ( matches.arrayIndices.indexOf( idx ) !== -1 )
        item = highlightText( item, matches[String( idx )] )
      items.push( crel( 'li', item ) )
    }
  }
  return items
}

const updateRecipes = function( recipes ) {
  // Delete recipes
  const el = document.getElementById( 'crel-content' )
  if ( el )
    el.remove()
  // Create new container and iterate over recipes
  for ( let recipe of recipes ) {
    const rcp = recipe.item
    // Identify locations of Fuse matches
    const matchLookup = unwrapHighlights( recipe.matches )
    // Identify matching regions in title, if any
    let titleMatches = []
    if ( 'title' in matchLookup )
      titleMatches = matchLookup.title['0']
    // Add link to recipe source, if one exists
    let sourceLink = crel( 'span', '' )
    if ( rcp.source.indexOf( 'http' )  >= 0 )
      sourceLink = crel( 'a', {'href': rcp.source}, crel( 'i', '(Source)' ) )

    let additionalNotes = crel( 'span', '' )
    if ( rcp.notes.length > 0 ) {
      additionalNotes = crel( 'div',
        crel( 'p', 'Notes:' ),
        crel( 'ul', createList( rcp, 'notes', matchLookup ) )
      )
    }
    // TODO: Set order that elements are added to DOM
    crel( document.getElementById( 'crel-target' ),
      // Add Recipe Title with Link
      crel( 'div', {'class': 'row br'},
        crel( 'h5', {'class': 'twelve columns', 'id': rcp.id},
          crel( 'a',
            {'class': 'unstyled', 'href': `#${rcp.id}`, 'id': `${rcp.id}`},
            highlightText( rcp.title, titleMatches )
          ),
          crel( 'span', ' ' ),
          sourceLink
        )
      ),
      // Add the Image and Recipe
      crel( 'div', {'class': 'row'},
        crel( 'img', {'alt': rcp.id, 'class': 'five columns', 'src': rcp.imgSrc} ),
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

//
// Search local recipe database
//

// TODO: Add text input and button event click to update search results
// var searchPhrase = 'instant pot'

// FIXME: freeze doesn't highlight for cake pops
var searchPhrase = 'freeze'
// // FIXME: Chocolate is missing highlights as well
// var searchPhrase = 'chocolate
// // Title highlighting works!
// var searchPhrase = 'cake'
// // FIXME: doesn't highlight headers...
// var searchPhrase = 'ingredients'

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

//
// Add matched recipes to view
//

updateRecipes( fuseResults )
