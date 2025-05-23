"use client";

import { useState, useEffect, Suspense } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { User, Film } from "lucide-react";
import { useRouter } from "next/navigation";
import { apiService } from "@/lib/api-config";
import { SearchBar } from "@/components/ui/searchbar";
import { Navbar } from "@/components/ui/navbar";
import { MagnifyingGlassIcon } from "@radix-ui/react-icons";
import Paginator from "@/components/ui/paginator";
import RasaChatWidget from "@/components/ui/RasaChatWidget";

export default function ActorsPage() {
  const router = useRouter();
  const [actors, setActors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchType, setSearchType] = useState("actor");
  const [page, setPage] = useState(1);
  const [size] = useState(33); // items per page
  const [total, setTotal] = useState(0);

  const fetchActors = async (newPage) => {
    setLoading(true);
    setPage(newPage);
    try {
      const response = await apiService.fetchData(`/actors?page=${newPage}&size=${size}`);
      if (response.ok) {
        const data = await response.json();
        const sortedActors = data.sort((a, b) => a.name.localeCompare(b.name));
        setActors(sortedActors);
      }
      const totalResponse = await apiService.fetchData('/actors_count');
      if (totalResponse.ok) {
        const totalData = await totalResponse.json();
        setTotal(totalData.total);
      }
    } catch (error) {
      console.error('Failed to fetch actors:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActors(1);
  }, []);

  const handleNavigation = (path) => {
    router.push(path);
  };

  const handleSearch = (query) => {
    router.push(`/?q=${encodeURIComponent(query)}&type=actor`);
  };

  const handleTypeChange = (newType) => {
    setSearchType(newType);
    setSearchQuery("");
    if (newType === "movie") {
      handleNavigation("/movies");
    }
  };

  const filteredActors = actors.filter(actor =>
    actor.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />
      <div className="p-8">
      <Card className="max-w-6xl mx-auto">
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle>🎭 All Actors</CardTitle>
              <p className="text-gray-500 mt-2">({total} actors)</p>
            </div>
            <div className="flex gap-4">
              <Button 
                variant="outline" 
                className="flex items-center gap-2"
                onClick={() => handleNavigation('/')}
              >
                <MagnifyingGlassIcon size={16} />
                Back to Home
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="mb-6">
            <Suspense>
              <SearchBar
                searchQuery={searchQuery}
                setSearchQuery={setSearchQuery}
                searchType={searchType}
                onSearch={handleSearch}
                onTypeChange={handleTypeChange}
                placeholder="Filter actors or search for details..."
              />
            </Suspense>
          </div>

          {loading ? (
            <div className="flex justify-center items-center h-96">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
            </div>
          ) : (
            <div className="max-h-[70vh] overflow-y-auto pr-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredActors.map((actor, index) => (
                  <Card 
                    key={index}
                    className="cursor-pointer hover:bg-gray-50"
                    onClick={() => handleNavigation(`/?q=${encodeURIComponent(actor.name)}&type=actor`)}
                  >
                    <CardContent className="p-4">
                      <h3 className="font-semibold">{actor.name}</h3>
                      <div className="mt-2 text-sm text-gray-500">
                        Click to see filmography
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}
          <Paginator
            page={page}
            total={total}
            size={size}
            onPageChange={fetchActors}
          />
        </CardContent>
      </Card>
      </div>
      <RasaChatWidget />
    </div>
  );
} 