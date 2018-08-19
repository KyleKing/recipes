'use strict'

// Default Highlighter class
export default class {

  // Take matches object and create lookup to more efficiently highlight matches in text
  unwrapHighlights ( fuseMatches ) {
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

  // Check for a match in lookup object key and index, then pass to highlight function
  highlightItem ( item, key, idx, matchObj ) {
    if ( key in matchObj && matchObj[key].arrayIndices.indexOf( idx ) !== -1 )
      return( this.highlightText( item, matchObj[key][String( idx )] ) )
    return( item )
  }

  // Wrap matched regions in given string with the highlight CSS class
  highlightText( text, regions ) {
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

}
