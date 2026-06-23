import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { LanguageProvider } from './context/LanguageContext';
import { Navbar } from './components/common';
import {
  HomePage,
  ChatPage,
  ExplorePage,
  DestinationDetailPage,
  RoutePlannerPage,
  AdminPage,
} from './pages';

function App() {
  return (
    <LanguageProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-background font-vietnam">
          <Navbar />
          <main>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/explore" element={<ExplorePage />} />
              <Route path="/destinations/:id" element={<DestinationDetailPage />} />
              <Route path="/route-planner" element={<RoutePlannerPage />} />
              <Route path="/admin" element={<AdminPage />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </LanguageProvider>
  );
}

export default App;
