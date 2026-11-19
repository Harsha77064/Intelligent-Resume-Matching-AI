import MatchingWorkspace from '../components/MatchingWorkspace'
import { PageHeader } from '../components/ui'

export default function Matching() {
  return (
    <>
      <PageHeader title="Resume Matching" subtitle="Choose a job, run matching, compare candidates and view matched / missing skills." />
      <MatchingWorkspace showRun />
    </>
  )
}
