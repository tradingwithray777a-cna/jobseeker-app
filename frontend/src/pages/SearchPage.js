import { useState, useEffect } from "react";
import axios from "axios";
import { Search, Download, Heart } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const SearchPage = () => {
  const [jobTitle, setJobTitle] = useState("");
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);

  const handleSearch = async () => {
    if (!jobTitle.trim()) {
      toast.error("Please enter a job title");
      return;
    }

    setSearching(true);
    try {
      toast.info("Searching job portals...");
      await axios.post(`${API}/jobs/search`, { job_title: jobTitle });
      const response = await axios.get(`${API}/jobs`);
      setJobs(response.data);
      toast.success(`Found ${response.data.length} jobs!`);
    } catch (error) {
      console.error("Error searching:", error);
      toast.error("Failed to search jobs");
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-violet-50 to-amber-50">
      <div className="bg-gradient-to-r from-violet-600 to-indigo-600 text-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-4xl sm:text-5xl font-bold mb-4" style={{fontFamily: 'Manrope, sans-serif'}}>
            Find Your Dream Job in Singapore
          </h1>
          <p className="text-lg text-violet-100 mb-8">Search from 200+ opportunities across MyCareersFuture & JobStreet</p>
          
          <div className="flex flex-col sm:flex-row gap-4 max-w-3xl">
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" />
              <Input
                type="text"
                placeholder="Enter job title (e.g., Software Engineer)"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                className="h-14 pl-12 pr-4 text-lg rounded-full"
                style={{background: 'white', color: '#0F172A'}}
              />
            </div>
            <Button
              onClick={handleSearch}
              disabled={searching}
              className="h-14 px-8 bg-amber-400 hover:bg-amber-500 text-slate-900 rounded-full font-semibold"
            >
              {searching ? "Searching..." : "Search Jobs"}
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {jobs.length > 0 ? (
          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-6" style={{fontFamily: 'Manrope, sans-serif'}}>
              {jobs.length} Jobs Found
            </h2>
            <div className="space-y-4">
              {jobs.map((job, index) => (
                <div key={job.id} className="bg-white rounded-2xl p-6 border border-slate-100 hover:shadow-lg transition-all">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="text-xl font-bold text-slate-900 mb-2" style={{fontFamily: 'Manrope, sans-serif'}}>
                        {job.job_title}
                      </h3>
                      <p className="text-slate-700 font-medium mb-1">{job.employer}</p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                      job.source === 'MyCareersFuture' 
                        ? 'bg-blue-50 text-blue-700' 
                        : 'bg-green-50 text-green-700'
                    }`}>
                      {job.source}
                    </span>
                  </div>
                  
                  <p className="text-sm text-slate-600 mb-4 line-clamp-2">{job.job_description}</p>
                  
                  <div className="flex flex-wrap gap-4 text-sm text-slate-600 mb-4">
                    <span>💰 {job.salary_range}</span>
                    <span>📅 Posted: {job.date_posted}</span>
                  </div>
                  
                  {job.ats_keywords && job.ats_keywords.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-4">
                      {job.ats_keywords.slice(0, 5).map((keyword, i) => (
                        <span key={i} className="px-2 py-1 bg-violet-50 text-violet-700 text-xs rounded-full">
                          {keyword}
                        </span>
                      ))}
                    </div>
                  )}
                  
                  <Button
                    onClick={() => window.open(job.employer_website, '_blank')}
                    className="bg-amber-400 hover:bg-amber-500 text-slate-900"
                  >
                    View Job Details
                  </Button>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="text-center py-16">
            <div className="w-24 h-24 bg-gradient-to-r from-violet-100 to-amber-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <Search className="w-12 h-12 text-violet-600" />
            </div>
            <h3 className="text-2xl font-bold text-slate-900 mb-2" style={{fontFamily: 'Manrope, sans-serif'}}>
              Start Your Job Search
            </h3>
            <p className="text-slate-600">Enter a job title above to search across multiple job portals</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SearchPage;
