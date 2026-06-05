import { redirect } from "next/navigation";

export default function Home() {
  // The dashboard layout enforces auth; unauthenticated users are bounced to /login.
  redirect("/vacancies");
}
