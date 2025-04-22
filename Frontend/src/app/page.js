"use client";

import { useState, useCallback, useEffect, useRef, Suspense } from "react";
import { User, Film } from "lucide-react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { SearchBar } from "@/components/ui/searchbar";
import { DetailsCard } from "@/components/ui/details";
import { apiService } from "@/lib/api-config";
import { WelcomeMessage } from "@/components/ui/welcome";
import Navbar from "@/components/ui/navbar";

// Dynamically import ForceGraph2D to avoid SSR issues
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
  loading: () => <p>Loading Graph...</p>,
});

const CypherQueryDisplay = ({ query }) => {
  if (!query) return null;

  return (
    <div className="mb-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
      <div className="flex justify-between items-center mb-2">
        <h3 className="font-semibold text-gray-700">Current Cypher Query</h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Click query to copy</span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              navigator.clipboard.writeText(query);
            }}
          >
            Copy
          </Button>
        </div>
      </div>
      <pre
        className="bg-white p-4 rounded-md overflow-x-auto text-sm font-mono text-gray-800"
        onClick={() => {
          navigator.clipboard.writeText(query);
        }}
        style={{ cursor: "pointer" }}
      >
        {query.split("\n").map((line, i) => (
          <div key={i} className="hover:bg-gray-50">
            {line}
          </div>
        ))}
      </pre>
    </div>
  );
};

const capitalizeWords = (str) => {
  // Check if string is mixed case (has both upper and lower case letters)
  const hasMixedCase = str !== str.toUpperCase() && str !== str.toLowerCase();
  
  // If mixed case, return original string unchanged
  if (hasMixedCase) {
    return str;
  }
  
  // Otherwise, apply the capitalization transformation
  return str
    .toLowerCase()
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
};

const addActorFromTMDB = async (actorName) => {
  try {
    const formattedName = capitalizeWords(actorName.trim());

    const response = await apiService.postData(
      `/add_actor_from_tmdb/${encodeURIComponent(formattedName)}`
    );

    if (!response.ok) {
      throw new Error("Failed to add actor");
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error adding actor:", error);
    throw error;
  }
};

const NotFoundMessage = ({ type, query, onAddActor }) => (
  <div className="text-center py-12">
    <div className="mb-4">
      <span className="text-6xl">🔍</span>
    </div>
    <h2 className="text-2xl font-bold mb-2">
      No {capitalizeWords(type)} Found
    </h2>
    <p className="text-gray-600 mb-6">
      We couldn't find any {type === "actor" ? "actor" : "movie"} matching "
      {query}"
    </p>
    {type === "actor" && (
      <div className="space-y-4">
        <p className="text-sm text-gray-500">
          Would you like to add this actor from TMDB?
        </p>
        <Button onClick={onAddActor} className="bg-blue-500 hover:bg-blue-600">
          Add Actor from TMDB
        </Button>
      </div>
    )}
  </div>
);

export default function Home() {
  const router = useRouter();
  const ForceGraphRef = useRef();
  const graphReady = useRef(false)

  const [searchQuery, setSearchQuery] = useState("");
  const [searchType, setSearchType] = useState("actor");
  const [searchResults, setSearchResults] = useState(null);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [currentQuery, setCurrentQuery] = useState("");
  const [showCypherQuery, setShowCypherQuery] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [lastSearchedQuery, setLastSearchedQuery] = useState("");
  const [hasActors, setHasActors] = useState(true);
  const [isSeeding, setIsSeeding] = useState(false);
  const [toast, setToast] = useState(null);


  // Initialize state from URL on component mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const query = params.get("q");
    const type = params.get("type");

    if (query) {
      setSearchQuery(query);
      setSearchType(type || "actor");
      handleSearch(query, type || "actor");
    }
  }, []);

  // Update URL when search is performed
  const updateURL = (query, type) => {
    const params = new URLSearchParams();
    const formattedQuery = type === "actor" ? capitalizeWords(query) : query;
    params.set("q", formattedQuery);
    params.set("type", type);
    router.push(`/?${params.toString()}`, { scroll: false });
  };

  const transformToGraphData = (data, type) => {
    const nodes = [];
    const links = [];

    if (type === "actor" && data?.actor && data?.movies) {
      // Add actor node
      nodes.push({
        id: data.actor.name,
        name: data.actor.name,
        type: "actor",
        val: 45,
        collisionRadius: 80,
      });

      // Add movie nodes and connections (limit to first 29 movies)
      data.movies.slice(0, 29).forEach((movie) => {
        nodes.push({
          id: movie.title,
          name: movie.title,
          type: "movie",
          val: 40,
          year: movie.year,
          collisionRadius: 75,
        });

        links.push({
          source: data.actor.name,
          target: movie.title,
          distance: 500,
        });
      });
    } else if (type === "movie" && data?.movie && data?.actors) {
      // Add movie node in the center
      nodes.push({
        id: data.movie.title,
        name: data.movie.title,
        type: "movie",
        val: 45,
        year: data.movie.year,
        collisionRadius: 80,
      });

      // Add actor nodes and connections (limit to first 29 actors)
      data.actors.slice(0, 29).forEach((actor) => {
        nodes.push({
          id: actor.name,
          name: actor.name,
          type: "actor",
          val: 40,
          collisionRadius: 75,
        });

        links.push({
          source: data.movie.title,
          target: actor.name,
          distance: 500,
        });
      });
    }

    return { nodes, links };
  };
  const handleTypeChange = (newType) => {
    setSearchType(newType);
    setSearchQuery("");
    setSelectedNode(null);
    setSearchResults(null);
    setGraphData({ nodes: [], links: [] });
    setCurrentQuery("");
    setNotFound(false);
    setLastSearchedQuery("");

    router.push("/", { scroll: false });
  };

  useEffect(() => {
    // console.log("Triggering!");
    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);
      const query = params.get("q");
      const type = params.get("type");

      if (query) {
        setSearchQuery(query);
        setSearchType(type || "actor");
        handleSearch(query, type || "actor");
      } else {
        // Reset state when navigating to empty URL
        setSearchQuery("");
        setSearchType("actor");
        setSelectedNode(null);
        setSearchResults(null);
        setGraphData({ nodes: [], links: [] });
        setCurrentQuery("");
        setNotFound(false);
      }
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    // console.log("Triggering!");
    const checkForActors = async () => {
      try {
        const response = await apiService.fetchData("/actors");
        const data = await response.json();
        setHasActors(data && data.length > 0);
      } catch (error) {
        console.error("Error checking for actors:", error);
        setHasActors(false);
      }
    };

    checkForActors();
  }, []);

  const handleSeedActors = async () => {
    setIsSeeding(true);
    const startTime = Date.now();

    setToast({
      title: 'Seeding Database',
      description: 'Adding actors and their filmographies...',
      loading: true
    });
  
    try {
      const response = await apiService.postData('/seed/actors');
      if (response.ok) {
        const data = await response.json();
        const duration = ((Date.now() - startTime) / 1000).toFixed(1);
        
        // Show success toast
        setToast({
          title: 'Database Seeded!',
          description: `Added ${data.total_successful} actors in ${duration}s`,
          loading: false
        });
        
        // Clear toast after 5 seconds
        setTimeout(() => setToast(null), 5000);
        setHasActors(true);
      }
    } catch (error) {
      console.error('Error seeding actors:', error);
      setToast({
        title: 'Seeding Failed',
        description: 'Please try again',
        loading: false
      });
      setTimeout(() => setToast(null), 3000);
      setError('Failed to seed actors. Please try again.');
    } finally {
      setIsSeeding(false);
    }
  };

  const handleSearch = async (query = searchQuery, type = searchType) => {
    if (!query.trim()) return;

    const formattedQuery = type === "actor" ? capitalizeWords(query) : query;

    const params = new URLSearchParams();
    params.set("q", formattedQuery);
    params.set("type", type);
    window.history.pushState({}, "", `/?${params.toString()}`);

    setLoading(true);
    setError(null);
    setNotFound(false);
    setSelectedNode(null);
    setLastSearchedQuery(formattedQuery);
    updateURL(formattedQuery, type);

    // Set the current Cypher query based on search type
    const cypherQuery =
      type === "actor"
        ? `MATCH (a:Actor {name: "${formattedQuery}"})-[:ACTED_IN]->(m:Movie)
WITH a as actor, m
ORDER BY m.year DESC, m.title
WITH actor, collect(m) as movies
RETURN actor, movies`
        : `MATCH (m:Movie {title: "${formattedQuery}"})
OPTIONAL MATCH (a:Actor)-[:ACTED_IN]->(m)
WITH m as movie, a
ORDER BY a.name
WITH movie, collect(a) as actors
RETURN movie, actors`;

    setCurrentQuery(cypherQuery);

    try {
      const response = await apiService.fetchData(
        `/${type}s/${encodeURIComponent(formattedQuery)}/${
          type === "actor" ? "filmography" : "cast"
        }`
      );

      if (response.status === 404) {
        setNotFound(true);
        setSearchResults(null);
        setGraphData({ nodes: [], links: [] });
        setLoading(false);
        return;
      }

      if (!response.ok) {
        throw new Error(`Search failed: ${response.status}`);
      }

      const data = await response.json();

      // Check if the response is empty

      if (
        !data ||
        (type === "actor" && (!data.actor || !data.movies?.length)) ||
        (type === "movie" && (!data.movie || !data.actors?.length))
      ) {
        setNotFound(true);
        setSearchResults(null);
        setGraphData({ nodes: [], links: [] });
      } else {
        setSearchResults(data);
        setGraphData(transformToGraphData(data, type));
      }
    } catch (err) {
      console.error("Search error:", err);
      setError("Failed to fetch data. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleNodeClick = useCallback(async (node) => {
    setSelectedNode(node);

    // If clicking on a movie node, search for that movie's cast
    if (node.type === "movie") {
      setSearchQuery(node.name);
      setSearchType("movie");
      await handleSearch(node.name, "movie");
    }
    // If clicking on an actor node, search for that actor's filmography
    else if (node.type === "actor") {
      setSearchQuery(node.name);
      setSearchType("actor");
      await handleSearch(node.name, "actor");
    }
  }, []);

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const handleAddActor = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await addActorFromTMDB(searchQuery);

      // After successfully adding the actor, perform a new search
      if (result) {
        await handleSearch(searchQuery, "actor");
      }
    } catch (error) {
      setError("Failed to add actor from TMDB. Please try again.");
      setNotFound(true); // Keep the not found state if addition fails
    } finally {
      setLoading(false);
    }
  };

  const handleNavigation = (path) => {
    // Reset all states
    setSearchQuery("");
    setSelectedNode(null);
    setSearchResults(null);
    setGraphData({ nodes: [], links: [] });
    setCurrentQuery("");
    setNotFound(false);
    setLastSearchedQuery("");

    // Navigate to the new path
    router.push(path);
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />
      <div className="p-8">
      <Card className="max-w-6xl mx-auto">
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle>🎬 Movie Database Explorer 🍿</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <Suspense>
            <SearchBar
              searchQuery={searchQuery}
              setSearchQuery={setSearchQuery}
              searchType={searchType}
              onSearch={(suggestion) => handleSearch(suggestion || searchQuery)}
              onTypeChange={handleTypeChange}
            />
          </Suspense>
          {!hasActors && (
            <WelcomeMessage
              onSeedActors={handleSeedActors}
              isLoading={isSeeding}
            />
          )}

          {error && (
            <div className="text-red-500 mb-4 p-4 bg-red-50 rounded-lg mt-4">
              {error}
            </div>
          )}
          {error && (
            <div className="text-red-500 mb-4 p-4 bg-red-50 rounded-lg">
              {error}
            </div>
          )}

          {loading ? (
            <div className="flex justify-center items-center h-96">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
            </div>
          ) : notFound ? (
            <NotFoundMessage
              type={searchType}
              query={lastSearchedQuery}
              onAddActor={handleAddActor}
            />
          ) : graphData.nodes.length > 0 ? (
            <div className="space-y-8">
              {searchResults && (
                <DetailsCard data={searchResults} type={searchType} />
              )}
              {/* Add Checkbox Toggle */}
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="show-cypher"
                  checked={showCypherQuery}
                  onCheckedChange={setShowCypherQuery}
                />
                <label
                  htmlFor="show-cypher"
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                >
                  Show Cypher Query
                </label>
              </div>

              {/* Conditionally Render CypherQueryDisplay */}
              {showCypherQuery && <CypherQueryDisplay query={currentQuery} />}

              {/* Graph Visualization */}
              <div className="h-[600px] border rounded-lg overflow-hidden bg-white relative">
                <ForceGraph2D
                  // ref={ForceGraphRef}
                  graphData={graphData}
                  nodeLabel="name"
                  nodeColor={(node) =>
                    selectedNode?.id === node.id
                      ? "#fbbf24"
                      : node.type === "actor"
                      ? "#ff6b6b"
                      : "#4ecdc4"
                  }
                  width={window.innerWidth * 0.65}
                  height={600}
                  centerAt={[window.innerWidth * 0.25, 300]}
                  nodeRelSize={8}
                  linkWidth={2}
                  linkColor={() => "#cbd5e1"}
                  backgroundColor="#ffffff"
                  onNodeClick={handleNodeClick}
                  enableZoom={true}
                  minZoom={0.5}
                  maxZoom={4}
                  // cooldownTicks={50}
                  linkDistance={100}
                  d3AlphaDecay={0.02}
                  d3VelocityDecay={0.3}
                  // autoPauseRedraw={false}
                  nodeCanvasObject={(node, ctx, globalScale) => {
                    const label = node.name;
                    const fontSize = 12 / globalScale;
                    const isSelected = selectedNode?.id === node.id;

                    ctx.beginPath();
                    ctx.arc(
                      node.x,
                      node.y,
                      isSelected ? 8 : 5,
                      0,
                      2 * Math.PI,
                      false
                    );
                    ctx.fillStyle = isSelected
                      ? "#fbbf24"
                      : node.type === "actor"
                      ? "#ff6b6b"
                      : "#4ecdc4";
                    ctx.fill();

                    if (isSelected) {
                      ctx.strokeStyle = "#f59e0b";
                      ctx.lineWidth = 2;
                      ctx.stroke();
                    }

                    ctx.font = `${fontSize}px Sans-Serif`;
                    ctx.textAlign = "center";
                    ctx.textBaseline = "middle";
                    ctx.fillStyle = "#000000";
                    ctx.fillText(label, node.x, node.y + 12);
                  }}
                  onEngineStop={() => {
                    // if (graphReady.current) return;
                    // graphReady.current = true; // ensure only runs once

                    const graphBounds = {
                      x: { min: Infinity, max: -Infinity },
                      y: { min: Infinity, max: -Infinity },
                    };

                    graphData.nodes.forEach((node) => {
                      graphBounds.x.min = Math.min(
                        graphBounds.x.min,
                        node.x || 0
                      );
                      graphBounds.x.max = Math.max(
                        graphBounds.x.max,
                        node.x || 0
                      );
                      graphBounds.y.min = Math.min(
                        graphBounds.y.min,
                        node.y || 0
                      );
                      graphBounds.y.max = Math.max(
                        graphBounds.y.max,
                        node.y || 0
                      );
                    });

                    const graphWidth = graphBounds.x.max - graphBounds.x.min;
                    const graphHeight = graphBounds.y.max - graphBounds.y.min;
                    const graphCenter = {
                      x: (graphBounds.x.min + graphWidth / 2) * 0.6,
                      y: graphBounds.y.min + graphHeight / 2,
                    };

                    const zoomLevel =
                      Math.min(
                        (window.innerWidth * 0.65) / graphWidth,
                        600 / graphHeight
                      ) * 0.9;

                    ForceGraphRef.current?.centerAt(
                      graphCenter.x,
                      graphCenter.y,
                      1000
                    );
                    ForceGraphRef.current?.zoom(zoomLevel, 1000);
                  }}
                />
              </div>
              {/* Graph Legend */}
              <div className="flex gap-4 justify-center text-sm">
                <div className="flex items-center">
                  <div className="w-3 h-3 rounded-full bg-[#ff6b6b] mr-2"></div>
                  <span>Actors</span>
                </div>
                <div className="flex items-center">
                  <div className="w-3 h-3 rounded-full bg-[#4ecdc4] mr-2"></div>
                  <span>Movies</span>
                </div>
              </div>
              <p className="text-sm text-gray-500 mt-2 text-center italic">
                * Graph visualization shows only the first 25 connections for
                better readability. See complete list below.
              </p>
              {/* Results List */}
              <div className="space-y-4">
                <div className="flex items-center justify-between px-2">
                  <h2 className="text-xl font-semibold">
                    {searchType === "actor"
                      ? "Filmography (Newest First)"
                      : "Cast (Alphabetical)"}
                  </h2>
                  <div className="text-sm text-gray-500">
                    {searchType === "actor" && searchResults?.movies
                      ? `${searchResults.movies.length} movies`
                      : searchType === "movie" && searchResults?.actors
                      ? `${searchResults.actors.length} actors`
                      : ""}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {searchType === "actor" && searchResults?.movies
                    ? searchResults.movies.map((movie, index) => (
                        <Card
                          key={index}
                          className={`cursor-pointer transition-colors ${
                            selectedNode?.id === movie.title
                              ? "bg-yellow-50 border-yellow-400"
                              : ""
                          }`}
                          onClick={() =>
                            handleNodeClick({
                              id: movie.title,
                              name: movie.title,
                              type: "movie",
                              year: movie.year,
                            })
                          }
                        >
                          <CardContent className="p-4">
                            <div className="flex justify-between items-start">
                              <h3 className="font-semibold">{movie.title}</h3>
                              {movie.year && (
                                <span className="text-sm font-medium bg-gray-100 px-2 py-1 rounded">
                                  {movie.year}
                                </span>
                              )}
                            </div>
                            <div className="mt-2 text-sm text-gray-500">
                              Click to see cast
                            </div>
                          </CardContent>
                        </Card>
                      ))
                    : searchType === "movie" && searchResults?.actors
                    ? searchResults.actors.map((actor, index) => (
                        <Card
                          key={index}
                          className={`cursor-pointer transition-colors ${
                            selectedNode?.id === actor.name
                              ? "bg-yellow-50 border-yellow-400"
                              : ""
                          }`}
                          onClick={() =>
                            handleNodeClick({
                              id: actor.name,
                              name: actor.name,
                              type: "actor",
                            })
                          }
                        >
                          <CardContent className="p-4">
                            <div className="flex justify-between items-start">
                              <h3 className="font-semibold">{actor.name}</h3>
                            </div>
                            <div className="mt-2 text-sm text-gray-500">
                              Click to see filmography
                            </div>
                          </CardContent>
                        </Card>
                      ))
                    : null}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center text-gray-500 h-96 flex items-center justify-center">
              Search for {searchType === "actor" ? "an actor" : "a movie"} to
              see their connections
            </div>
          )}
        </CardContent>
      </Card>
      </div>
    </div>
  );
}
