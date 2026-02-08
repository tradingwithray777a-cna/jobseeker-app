import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import "@/App.css";
import { Search, Heart, Bell } from "lucide-react";

const Navigation = () => {
  const location = useLocation();
  const isActive = (path) => location.pathname === path;
  
  return (
    <nav className="bg-white border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link to="/" className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-r from-violet-600 to-indigo-600 rounded-full flex items-center justify-center">
              <Search className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-slate-900" style={{fontFamily: 'Manrope, sans-serif'}}>JobPulse SG</span>
          </Link>
          
          <div className="flex space-x-1">
            <Link
              to="/"
              data-testid="nav-search-link"
              className={`px-4 py-2 rounded-full font-medium transition-all ${
                isActive('/') 
                  ? 'bg-violet-600 text-white shadow-lg shadow-violet-500/30' 
                  : 'text-slate-600 hover:text-violet-600 hover:bg-violet-50'
              }`}
            >
              <Search className="w-4 h-4 inline mr-2" />
              Search
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
};

const Home = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-violet-50 to-amber-50">
      <div className="bg-gradient-to-r from-violet-600 to-indigo-600 text-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-4xl sm:text-5xl font-bold mb-4" style={{fontFamily: 'Manrope, sans-serif'}}>
            Find Your Dream Job in Singapore
          </h1>
          <p className="text-lg text-violet-100 mb-8">Search from 200+ opportunities across MyCareersFuture & JobStreet</p>
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
        <div className="w-24 h-24 bg-gradient-to-r from-violet-100 to-amber-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <Search className="w-12 h-12 text-violet-600" />
        </div>
        <h3 className="text-2xl font-bold text-slate-900 mb-2" style={{fontFamily: 'Manrope, sans-serif'}}>Coming Soon!</h3>
        <p className="text-slate-600">Job search functionality will be available shortly.</p>
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="App min-h-screen bg-slate-50">
      <BrowserRouter>
        <Navigation />
        <Routes>
          <Route path="/" element={<Home />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
