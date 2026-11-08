#ifndef HOSTMAP_READY_HPP
#define HOSTMAP_READY_HPP
#include <set>
#include <string>
namespace hostmap {
class Ready {
    std::string roster;
    std::set<unsigned> eligible, votes;
    bool allowed = false;
public:
    bool sync(const std::string& fingerprint, const std::set<unsigned>& players, bool canStart) {
        bool changed = fingerprint != roster || eligible != players || !canStart;
        if (changed) votes.clear();
        roster = fingerprint;
        eligible = players;
        allowed = canStart;
        return changed;
    }
    bool vote(unsigned player) {
        if (allowed && eligible.count(player)) votes.insert(player);
        return complete();
    }
    bool complete() const { return allowed && !eligible.empty() && votes == eligible; }
    unsigned count() const { return static_cast<unsigned>(votes.size()); }
    unsigned total() const { return static_cast<unsigned>(eligible.size()); }
    void clear() { votes.clear(); }
};
}
#endif
