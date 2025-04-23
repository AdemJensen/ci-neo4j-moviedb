import { useState, useEffect } from 'react';
import { Film, User, RefreshCw, X } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { apiService } from '@/lib/api-config';

// Simple Notification component
const Notification = ({ message, type, onClose }) => (
  <div className={`
    fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg flex items-center gap-2
    ${type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}
  `}>
    <span>{message}</span>
    <button 
      onClick={onClose}
      className="p-1 hover:bg-white/20 rounded-full"
    >
      <X className="w-4 h-4" />
    </button>
  </div>
);

const DetailsCard = ({ data, type, onDataUpdate }) => {
  const [posterUrl, setPosterUrl] = useState(null);
  const [isLoadingPoster, setIsLoadingPoster] = useState(false);
  const [isUpdatingActor, setIsUpdatingActor] = useState(false);
  const [notification, setNotification] = useState(null);
  const [actorData, setActorData] = useState(data);

  const showNotification = (message, type = 'success') => {
    setNotification({ message, type });
    // Auto-hide after 3 seconds
    setTimeout(() => {
      setNotification(null);
    }, 3000);
  };

  // Refresh actor data from backend
  const refreshActorData = async (actorName) => {
    try {
      const response = await apiService.fetchData(
        `/actors/${encodeURIComponent(actorName)}/filmography`
      );
      if (response.ok) {
        const newData = await response.json();
        setActorData(newData);
        if (onDataUpdate) {
          onDataUpdate(newData);
        }
      }
    } catch (error) {
      console.error('Error refreshing actor data:', error);
    }
  };

  const updateActorData = async (actorName) => {
    setIsUpdatingActor(true);
    try {
      const updateResponse = await apiService.postData(
        `/actors_update/${encodeURIComponent(actorName)}`,
          { "name": actorName, "actor": null, "manually": false }
      );
      
      if (updateResponse.ok) {
        await refreshActorData(actorName);
        showNotification('Actor information updated successfully');
      } else {
        throw new Error('Failed to update actor information');
      }
    } catch (error) {
      console.error('Error updating actor data:', error);
      showNotification('Failed to update actor information', 'error');
    } finally {
      setIsUpdatingActor(false);
    }
  };

  const updateMovieData = async (movieTitle) => {
    setIsUpdatingActor(true);
    try {
      const updateResponse = await apiService.postData(
        `/add_movie_from_tmdb/${encodeURIComponent(movieTitle)}`,
          {  }
      );

      if (updateResponse.ok) {
        showNotification('Movie information updated successfully, please refresh the page.');
      } else {
        throw new Error('Failed to update movie information');
      }
    } catch (error) {
      console.error('Error updating movie data:', error);
      showNotification('Failed to update movie information', 'error');
    } finally {
      setIsUpdatingActor(false);
    }
  };

  // Update local state when props change
  useEffect(() => {
    setActorData(data);
  }, [data]);

  useEffect(() => {
    const fetchMoviePoster = async () => {
      if (type !== 'movie' || !data?.movie?.title) return;

      setIsLoadingPoster(true);
      try {
        const response = await apiService.fetchData(
          `/movie/poster/${encodeURIComponent(data.movie.title)}`
        );
        
        if (response.ok) {
          const posterData = await response.json();
          if (posterData.poster_path) {
            setPosterUrl(`https://image.tmdb.org/t/p/w500${posterData.poster_path}`);
          }
        }
      } catch (error) {
        console.error('Error fetching movie poster:', error);
      } finally {
        setIsLoadingPoster(false);
      }
    };

    fetchMoviePoster();
  }, [data?.movie?.title, type]);

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    } catch (error) {
      return dateString;
    }
  };

  const calculateAge = (birthDate, deathDate) => {
    if (!birthDate) return null;
    
    const birth = new Date(birthDate);
    const end = deathDate ? new Date(deathDate) : new Date();
    
    let age = end.getFullYear() - birth.getFullYear();
    const monthDiff = end.getMonth() - birth.getMonth();
    
    if (monthDiff < 0 || (monthDiff === 0 && end.getDate() < birth.getDate())) {
      age--;
    }
    
    return age;
  };

  if (!data) return null;

  // Actor Card
  if (type === 'actor' && actorData?.actor && actorData?.movies) {
    const { actor, movies } = actorData;
    const imageUrl = actor?.profile_path ? 
      `https://image.tmdb.org/t/p/w185${actor.profile_path}` : 
      null;

    const age = calculateAge(actor.date_of_birth, actor.date_of_death);
    const sortedMovies = [...movies].sort((a, b) => (b.year || '0') - (a.year || '0'));
    
    return (
      <>
        {notification && (
          <Notification
            message={notification.message}
            type={notification.type}
            onClose={() => setNotification(null)}
          />
        )}
        
        <Card className="mb-4">
          <CardContent className="p-6">
            <div className="flex gap-6">
              <div className="flex-shrink-0 w-32 h-40 relative">
                {imageUrl ? (
                  <img
                    src={imageUrl}
                    alt={actor.name}
                    className="w-full h-full object-cover rounded-lg shadow-md"
                  />
                ) : (
                  <div className="w-full h-full bg-gray-200 rounded-lg shadow-md flex flex-col items-center justify-center gap-2">
                    <User className="w-12 h-12 text-gray-400" />
                    {!isUpdatingActor ? (
                      <button 
                        onClick={() => updateActorData(actor.name)}
                        className="px-2 py-1 text-xs text-gray-600 hover:text-gray-900 flex items-center gap-1
                                 bg-white/50 hover:bg-white/80 rounded transition-colors"
                      >
                        <RefreshCw className="w-3 h-3" />
                        Update Info
                      </button>
                    ) : (
                      <div className="animate-spin">
                        <RefreshCw className="w-4 h-4 text-gray-400" />
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              <div className="flex-1">
                <div className="flex justify-between items-start mb-4">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <h2 className="text-2xl font-bold">{actor.name}</h2>
                      {!isUpdatingActor && (
                        <button 
                          onClick={() => updateActorData(actor.name)}
                          className="px-2 py-1 text-xs text-gray-600 hover:text-gray-900 flex items-center gap-1
                                   bg-gray-100 hover:bg-gray-200 rounded transition-colors"
                        >
                          <RefreshCw className="w-3 h-3" />
                          Update
                        </button>
                      )}
                      {isUpdatingActor && (
                          <div className="animate-spin">
                            <RefreshCw className="w-4 h-4 text-gray-400"/>
                          </div>
                      )}
                    </div>
                    <div className="space-y-1 text-sm">
                      {actor.gender && (
                          <p className="text-gray-600">
                          <span className="font-medium">Gender:</span> {actor.gender}
                        </p>
                      )}
                      {actor.date_of_birth && (
                        <p className="text-gray-600">
                          <span className="font-medium">Born:</span> {formatDate(actor.date_of_birth)}
                          {age && ` (${age} years${actor.date_of_death ? ' old at death' : ' old'})`}
                        </p>
                      )}
                      {actor.date_of_death && (
                        <p className="text-gray-600">
                          <span className="font-medium">Died:</span> {formatDate(actor.date_of_death)}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-col items-end">
                    <span className="text-sm text-gray-500">Movies</span>
                    <span className="font-medium text-lg">{movies.length}</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm mt-4">
                  {sortedMovies.length > 0 && (
                    <>
                      <div>
                        <span className="text-gray-500">Latest Movie</span>
                        <p className="font-medium">
                          {sortedMovies[0].title} 
                          {sortedMovies[0].year && ` (${sortedMovies[0].year})`}
                        </p>
                      </div>
                      <div>
                        <span className="text-gray-500">First Movie</span>
                        <p className="font-medium">
                          {sortedMovies[sortedMovies.length - 1].title}
                          {sortedMovies[sortedMovies.length - 1].year && 
                            ` (${sortedMovies[sortedMovies.length - 1].year})`}
                        </p>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </>
    );
  }

  // Movie Card
  if (type === 'movie' && data.movie && data.actors) {
    const { movie, actors } = data;

    return (
      <Card className="mb-4">
        <CardContent className="p-6">
          <div className="flex gap-6">
            <div className="flex-shrink-0 w-48 h-72 relative">
              {isLoadingPoster ? (
                <div className="w-full h-full bg-gray-200 animate-pulse rounded-lg" />
              ) : posterUrl ? (
                <img
                  src={posterUrl}
                  alt={movie.title}
                  className="w-full h-full object-cover rounded-lg shadow-md"
                  loading="lazy"
                />
              ) : (
                <div className="w-full h-full bg-gray-200 rounded-lg shadow-md flex items-center justify-center">
                  <Film className="w-12 h-12 text-gray-400" />
                </div>
              )}
            </div>
            
            <div className="flex-1">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <div className="flex items-center gap-2">

                  <h2 className="text-2xl font-bold mb-2">{movie.title} </h2>
                    {!isUpdatingActor && (
                    <button
                      onClick={() => updateMovieData(movie.title)}
                      className="px-2 py-1 text-xs text-gray-600 hover:text-gray-900 flex items-center gap-1
                               bg-gray-100 hover:bg-gray-200 rounded transition-colors"
                    >
                      <RefreshCw className="w-3 h-3" />
                      Update
                    </button>
                  )}
                    {isUpdatingActor && (
                        <div className="animate-spin">
                          <RefreshCw className="w-4 h-4 text-gray-400"/>
                        </div>
                    )}
                  </div>

                  <div className="space-y-1">
                    {movie.year && (
                        <p className="text-gray-600">
                        <span className="font-medium">Release Year:</span> {movie.year}
                      </p>
                    )}
                    <p className="text-gray-600">
                      <span className="font-medium">Cast:</span> {actors.length} {actors.length === 1 ? 'actor' : 'actors'} in database
                    </p>
                  </div>
                </div>
                {movie.rating && (
                  <div className="flex flex-col items-end">
                    <span className="text-sm text-gray-500">Rating</span>
                    <span className="font-medium text-lg">{movie.rating}</span>
                  </div>
                )}
              </div>

              {movie.overview && (
                <div className="mt-4">
                  <h3 className="text-sm font-medium text-gray-600 mb-1">Overview</h3>
                  <p className="text-sm text-gray-800">{movie.overview}</p>
                </div>
              )}

              <div className="mt-6">
                <h3 className="text-sm font-medium text-gray-600 mb-2">Cast</h3>
                <div className="flex flex-wrap gap-2">
                  {actors.map((actor, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-gray-100 text-gray-800"
                    >
                      {actor.name}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return null;
};

export { DetailsCard };