
// 
// Example ExRootAnalysis of MadGraph LHE files (QED electron annihilation)
//
// <MG> refers to location of MadGraph
//
// In MadGraph:
// 1) If not installed already "install ExRootAnalysis"
// 2) generate e+ e- > a > mu+ mu-
// 3) output demo
// 4) launch demo
// 5) adjust beam energy, if lower than ~100 GeV, you'll need to lower charged lepton pt threshold "ptl" in run_card.dat
//   - to agree with theory calculation, you'll need to make sure you use a consistent "aewm1" (alpha_EW) in param_card.dat
//     - also for good agreement, you'll want to increase the maximum eta for charged leptons "etal" in run_card.dat
// 
// Exit MadGraph, and do:
// 6) copy the lhe file:  cp <MG>/eeamumu/Events/run_01/unweighted_events.lhe.gz .
// 7) unzip it: gunzip unweighted_events.lhe.gz .
// 8) Make ROOT file:  <MG>/ExRootAnalysis/ExRootLHE unweighted_events.lhe lhe.root
// 9) Run this script:  root -x demo.C

demo(){
  //setup a rootlogon.C file to do this, or do it here, but you may need full path:
  gSystem->Load("./libDelphes.dylib");
  gSystem->Load("libPhysics");

  TChain chain("LHEF");
  chain.Add("demo.root");
  ExRootTreeReader *treeReader = new ExRootTreeReader(&chain);
  Long64_t numberOfEntries = treeReader->GetEntries();



  TClonesArray *branchGen = treeReader->UseBranch("Particle");  

  for(Long64_t entry = 0; entry < numberOfEntries; ++entry){
    treeReader->ReadEntry(entry);
    int ngen = branchGen->GetEntries();
    for (int i=0; i<ngen; i++){
      TRootGenParticle * part = (TRootGenParticle*) branchGen->At(i);
      int pid = part->PID;

      //double px = part->Px;
      //double py = part->Py;
      //double pz = part->Pz;
      //double e  = part->E;      
      // at least in my install, there is a little bug:
      double px = part->E;
      double py = part->Px;
      double pz = part->Py;
      double e  = part->Pz;

      cout << pid << ":  px=" << px << ", py=" << py << ", pz=" << pz << ", e=" << e << "\n";
    }
    if (entry>5) break;
  }
}
