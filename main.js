//
// Test text highlight function
// https://github.com/krisk/Fuse/issues/6#issuecomment-352192752
//

// Does not account for overlapping highlighted regions, if that exists at all O_o..
function generateHighlightedText( text, regions ) {
  if( !regions ) return text

  var content = '',
    nextUnhighlightedRegionStartingIndex = 0

  regions.forEach( ( region ) => {
    content += '' +
      text.substring( nextUnhighlightedRegionStartingIndex, region[0] ) +
      '<span class="highlight">' +
        text.substring( region[0], region[1] ) +
      '</span>' +
    ''
    nextUnhighlightedRegionStartingIndex = region[1]
  } )

  content += text.substring( nextUnhighlightedRegionStartingIndex )

  return content
}

var srcText = 'hello world' // assume this is the srcText
console.log( generateHighlightedText( srcText, [[1, 3], [6, 8]] ) )
// h<span class="highlight">el</span>lo <span class="highlight">wo</span>rld

//
// Test creating HTML with Crel
//

const createCheckedItem = function( list ) {
  const items = []
  for ( let idx = 0; idx < list.length; idx++ ) {
    const item = list[idx]
    items.push( crel( 'input',
      {
        'class': 'ingredient magic-checkbox INGREDIENT', // TODO: Ingredient name?
        'id': String( idx ), // TODO: Unique Index for all headers
        'name': 'layout',
        'type': 'checkbox',
      } ) )
    items.push( crel( 'label', {'for': String( idx )}, item ) )
  }
  return items
}

const constCreateListGroup = function( ingObj ) {
  let items = []
  for ( let header of Object.keys( ingObj ) ) {
    items.push( crel( 'p', header ) )
    items.push( crel( 'ul',
      createCheckedItem( ingObj[header] )
    ) )
  }
  return items
}

const createList = function( list ) {
  const items = []
  for ( let item of list )
    items.push( crel( 'li', item ) )
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
    // TODO: Set order that elements are added to DOM
    crel( document.getElementById( 'crel-target' ),
      // Add Recipe Title with Link
      // TODO: Add source link?
      crel( 'div', {'class': 'row br'},
        crel( 'h5', {'class': 'twelve columns', 'id': rcp.id},
          crel( 'a',
            {'class': 'unstyled', 'href': `#${rcp.id}`, 'id': `${rcp.id}`},
            `# ${rcp.title}`
          )
        )
      ),
      // Add the Image and Recipe
      crel( 'div', {'class': 'row'},
        crel( 'img', {'alt': rcp.id, 'class': 'five columns', 'src': rcp.imgSrc} ),
        crel( 'div', {'class': 'seven columns', 'id': rcp.id},
          constCreateListGroup( rcp.ingredients ),
          crel( 'ol',
            createList( rcp.recipe )
          ),
          crel( 'p', 'Notes:' ),
          crel( 'ul',
            createList( rcp.notes )
          )
        )
      )
    )
  }
}

//
// Test Searching database
//

const options = {
  distance: 100,
  includeMatches: true,
  keys: localDB.searchKeys,
  location: 0,
  maxPatternLength: 32,
  minMatchCharLength: 4,
  shouldSort: true,
  threshold: 0.2,
}
var fuse = new Fuse( localDB.recipes, options )
const fuseResult = fuse.search( 'instant pot' )
console.log( fuseResult )
// console.log( fuse.search( 'dsrt' ) )

//
// Try adding matched recipes to view
//

updateRecipes( fuseResult )

