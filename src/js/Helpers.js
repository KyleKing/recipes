// Generate Star Icons based on rating number
export const addStars = function( rating ) {
  const stars = []
  for ( let idx = 0; idx < rating; idx++ )
    stars.push( crel( 'i', {'class': 'fas fa-star'} ) )
  return stars
}
