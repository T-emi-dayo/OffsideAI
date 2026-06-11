import { BrowserRouter, Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import FixtureHub from "./pages/FixtureHub";
import MatchView from "./pages/MatchView";

export default function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <Routes>
        <Route path="/" element={<FixtureHub />} />
        <Route path="/match/:id" element={<MatchView />} />
      </Routes>
    </BrowserRouter>
  );
}
