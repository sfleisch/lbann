////////////////////////////////////////////////////////////////////////////////
// Copyright (c) 2014-2016, Lawrence Livermore National Security, LLC. 
// Produced at the Lawrence Livermore National Laboratory. 
// Written by the LBANN Research Team (B. Van Essen, et al.) listed in
// the CONTRIBUTORS file. <lbann-dev@llnl.gov>
//
// LLNL-CODE-697807.
// All rights reserved.
//
// This file is part of LBANN: Livermore Big Artificial Neural Network
// Toolkit. For details, see http://software.llnl.gov/LBANN or
// https://github.com/LLNL/LBANN. 
//
// Licensed under the Apache License, Version 2.0 (the "Licensee"); you
// may not use this file except in compliance with the License.  You may
// obtain a copy of the License at:
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
// implied. See the License for the specific language governing
// permissions and limitations under the license.
//
// lbann_layer_softmax .hpp .cpp - Softmax layer
////////////////////////////////////////////////////////////////////////////////

#ifndef LBANN_LAYER_SOFTMAX_HPP_INCLUDED
#define LBANN_LAYER_SOFTMAX_HPP_INCLUDED

#include "lbann/layers/lbann_layer.hpp"
//#include "lbann/layers/lbann_layer_fully_connected.hpp"
#include <string>



namespace lbann
{
    // CLayer : dense layer class
    class SoftmaxLayer: public Layer
    {
    public:
      SoftmaxLayer(uint index,
                   int numPrevNeurons,
                   uint numNeurons,
                   uint miniBatchSize,
                   weight_initialization init,
                   lbann_comm* comm,
                   Optimizer *optimizer);
        void setup(int numPrevNeurons);
        bool update();
      void summarize(lbann_summary& summarizer, int64_t step);
      void epoch_print() const;
      void epoch_reset();
        DataType checkGradient(Layer& PrevLayer, const DataType Epsilon=1e-4);
        //        void updateMB(const float LearnRate);
        DataType computeCost(const DistMat& Y);
        //        DataType computeCost(CircMat& Output);
        DataType WBL2norm();

        bool saveToCheckpoint(int fd, const char* filename, uint64_t* bytes);
        bool loadFromCheckpoint(int fd, const char* filename, uint64_t* bytes);

        bool saveToCheckpointShared(const char* dir, uint64_t* bytes);
        bool loadFromCheckpointShared(const char* dir, uint64_t* bytes);

        void resetCost();
        DataType avgCost() const;

    protected:
      void fp_set_std_matrix_view();
      void fp_linearity();
      void bp_linearity();
      void fp_nonlinearity() {}
      void bp_nonlinearity() {}

    public:
        DataType   WBL2NormSum;

    private:
        DataType aggregate_cost;   // if this type is changed, update checkpoint code
        long num_backprop_steps; // if this type is changed, update checkpoint code
        weight_initialization m_weight_initialization;
        ColSumMat ZsColMax;
        ColSumMat ZsNormExpSum;
        ColSumMat norms;
        StarMat ZsColMaxStar;
        StarMat ZsNormExpSumStar;
        DistMat Acts_Cost;
        DistMat m_activations_cost_v;
      /** Colume-wise sum of the costs of a minibatch. */
      ColSumMat m_minibatch_cost;
    };
}


#endif // LBANN_LAYER_SOFTMAX_HPP_INCLUDED
