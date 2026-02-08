import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import "@/App.css";
import { Search } from "lucide-react";
import SearchPage from "@/pages/SearchPage";

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

function App() {
  return (
    <div className="App min-h-screen bg-slate-50">
      <BrowserRouter basename="/jobseeker-app">
        <Navigation />
        <Routes>
          <Route path="/" element={<SearchPage />} />
        </Routes>
      <BrowserRouter>
    </div>
  );
}

export default App;
