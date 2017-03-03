from collections import namedtuple

import mxnet as mx

class RNN(object):
    """Implementation of a RNN.

    Args:
        data: the input mxnet symbol, usually a embedding layer.
        mask: if use mask, give the mask symbol, else is None.
        mode: 'lstm', 'gru'.
        seq_len: the length of padded sequence.

        ===============================================================================================
        real_seq_len: the length of real data. a list of batch size.
        Note: this should be consistent with mask and padding. remember where you pad.
        ===============================================================================================
        
        ***********************************************************************************************
        num_layers: layers number.
        Note: if you want to change the original formal for gru and lstm, for example, add a context vector
        to unit in every layer in each time step. For a 1-layer rnn, you can just concat it in the input data
        . For multi-layers, it is messy to change the rnn interface, so a good idea is to stack multi-layers 
        RNN, each layer is 1-layer RNN, then for higher-layer RNN, you can concat the context vector into
        the lower-layer hidden vector.
        ***********************************************************************************************
        
        bi_directional: True or False. 
        
        ===============================================================================================
        hidden_size: hidden state size. (the cell size is same as hidden size for LSTM)
        states: init states symbols, can be None then you need to provide the initial states during training. 
        cells: only needed for lstm, same as above.
        Note: the size of states and cells  should be consistent with hidden size, if not so, some error
        will occur, and it should be used with care.
        ===============================================================================================
        dropout: dropout between cells. 
        name: prefix for identify the symbol.

    Returns:
        a dict of [group of] mxnet symbol.
        {'last_time': {'hidden': value, 'cell': value}, 'last_layer': value}
        dict[last_time] contains all hiddens and cells of all layers
            in the last time. It is a list in following order:
                hidden: [hidden0, hidden1, hidden2, ....]
                cell: [cell0, cell1, cell2, .......]
            Note: for bi-directional, the forward_vrctor and backward_vector is concatted
            Note: the cells is None for gru.
        dict[last_layer] contains all hidden states of all times 
            in the last layer. It is a list in following order:
                [hidden0, hidden1, hidden2, ...]
            for bi-directional, the forward_hidden and backward_hidden is concatted
    Raise:

    """

    def __init__(self, data, mask=None, mode='lstm', seq_len=10, real_seq_len=None, 
                 num_layers=1, num_hidden=512, bi_directional=False, states=None, 
                 cells=None, dropout=0., name='rnn'):

        """ Initialization, define all need parameters and variables"""
        self.data = data
        self.mask = mask
        self.mode = mode
        self.seq_len = seq_len
        self.real_seq_len = real_seq_len
        self.num_layers = num_layers
        self.num_hidden = num_hidden
        self.bi_directional = bi_directional
        self.states = states
        self.cells = cells
        self.dropout = dropout
        self.name = name
        
        if self.mode == 'gru':
            self.GRUState = namedtuple("State", ["h"])
            self.GRUParam = namedtuple("Param", ["gates_i2h_weight", "gates_i2h_bias",
                                   "gates_h2h_weight", "gates_h2h_bias",
                                   "trans_i2h_weight", "trans_i2h_bias",
                                   "trans_h2h_weight", "trans_h2h_bias"])
        elif self.mode == 'lstm':
            self.LSTMState = namedtuple("State", ["c", "h"])
            self.LSTMParam = namedtuple("Param", ["i2h_weight", "i2h_bias", "h2h_weight", "h2h_bias"])
        else:
            raise Exception('Invalid mode.')

        self.setup_parameter()
        self.setup_init_states()
        

    def setup_parameter(self):
        """Setup parameters for rnn network"""
        if self.mode == 'gru':
            if not self.bi_directional:
                self.param_cells = []
                for i in xrange(self.num_layers):
                    self.param_cells.append(
                        self.GRUParam(
                            gates_i2h_weight = mx.sym.Variable("%s_l%d_i2h_gates_weight" % (self.name, i)),
                            gates_i2h_bias = mx.sym.Variable("%s_l%d_i2h_gates_bias" % (self.name, i)),
                            gates_h2h_weight = mx.sym.Variable("%s_l%d_h2h_gates_weight" % (self.name, i)),
                            gates_h2h_bias = mx.sym.Variable("%s_l%d_h2h_gates_bias" % (self.name, i)),
                            trans_i2h_weight = mx.sym.Variable("%s_l%d_i2h_trans_weight" % (self.name, i)),
                            trans_i2h_bias = mx.sym.Variable("%s_l%d_i2h_trans_bias" % (self.name, i)),
                            trans_h2h_weight = mx.sym.Variable("%s_l%d_h2h_trans_weight" % (self.name, i)),
                            trans_h2h_bias = mx.sym.Variable("%s_l%d_h2h_trans_bias" % (self.name, i))
                        )
                    )
            else:
                self.forward_param_cells = []
                self.backward_param_cells = []
                for i in xrange(self.num_layers):
                    self.forward_param_cells.append(
                        self.GRUParam(
                            gates_i2h_weight = mx.sym.Variable("%s_forward_l%d_i2h_gates_weight" % (self.name, i)),
                            gates_i2h_bias = mx.sym.Variable("%s_forward_l%d_i2h_gates_bias" % (self.name, i)),
                            gates_h2h_weight = mx.sym.Variable("%s_forward_l%d_h2h_gates_weight" % (self.name, i)),
                            gates_h2h_bias = mx.sym.Variable("%s_forward_l%d_h2h_gates_bias" % (self.name, i)),
                            trans_i2h_weight = mx.sym.Variable("%s_forward_l%d_i2h_trans_weight" % (self.name, i)),
                            trans_i2h_bias = mx.sym.Variable("%s_forward_l%d_i2h_trans_bias" % (self.name, i)),
                            trans_h2h_weight = mx.sym.Variable("%s_forward_l%d_h2h_trans_weight" % (self.name, i)),
                            trans_h2h_bias = mx.sym.Variable("%s_forward_l%d_h2h_trans_bias" % (self.name, i))
                        )
                    )
                    self.backward_param_cells.append(
                        self.GRUParam(
                            gates_i2h_weight = mx.sym.Variable("%s_backward_l%d_i2h_gates_weight" % (self.name, i)),
                            gates_i2h_bias = mx.sym.Variable("%s_backward_l%d_i2h_gates_bias" % (self.name, i)),
                            gates_h2h_weight = mx.sym.Variable("%s_backward_l%d_h2h_gates_weight" % (self.name, i)),
                            gates_h2h_bias = mx.sym.Variable("%s_backward_l%d_h2h_gates_bias" % (self.name, i)),
                            trans_i2h_weight = mx.sym.Variable("%s_backward_l%d_i2h_trans_weight" % (self.name, i)),
                            trans_i2h_bias = mx.sym.Variable("%s_backward_l%d_i2h_trans_bias" % (self.name, i)),
                            trans_h2h_weight = mx.sym.Variable("%s_backward_l%d_h2h_trans_weight" % (self.name, i)),
                            trans_h2h_bias = mx.sym.Variable("%s_backward_l%d_h2h_trans_bias" % (self.name, i))
                        )
                    )
        elif self.mode == 'lstm':
            if not self.bi_directional:
                self.param_cells = []
                for i in range(self.num_layers):
                    self.param_cells.append(
                        self.LSTMParam(
                            i2h_weight = mx.sym.Variable("%s_l%d_i2h_weight" % (self.name, i)),
                            i2h_bias = mx.sym.Variable("%s_l%d_i2h_bias" % (self.name, i)),
                            h2h_weight = mx.sym.Variable("%s_l%d_h2h_weight" % (self.name, i)),
                            h2h_bias = mx.sym.Variable("%s_l%d_h2h_bias" % (self.name, i))
                        )
                    )
            else:
                self.forward_param_cells = []
                self.backward_param_cells = []
                for i in xrange(self.num_layers):
                    self.forward_param_cells.append(
                        self.LSTMParam(
                            i2h_weight = mx.sym.Variable("%s_foward_l%d_i2h_weight" % (self.name, i)),
                            i2h_bias = mx.sym.Variable("%s_forward_l%d_i2h_bias" % (self.name, i)),
                            h2h_weight = mx.sym.Variable("%s_forward_l%d_h2h_weight" % (self.name, i)),
                            h2h_bias = mx.sym.Variable("%s_forward_l%d_h2h_bias" % (self.name, i))
                        )
                    )
                    self.backward_param_cells.append(
                        self.LSTMParam(
                            i2h_weight = mx.sym.Variable("%s_backward_l%d_i2h_weight" % (self.name, i)),
                            i2h_bias = mx.sym.Variable("%s_backward_l%d_i2h_bias" % (self.name, i)),
                            h2h_weight = mx.sym.Variable("%s_backward_l%d_h2h_weight" % (self.name, i)),
                            h2h_bias = mx.sym.Variable("%s_backward_l%d_h2h_bias" % (self.name, i))
                        )
                    )  
        else:
            pass

    def setup_init_states(self):
        """ setup initial states for rnn network"""
        if self.mode == 'gru':
            if not self.bi_directional:
                self.last_states = []
                for i in range(self.num_layers):
                    if self.states is not None:
                        tmp_h = self.states[i]
                    else:
                        tmp_h = mx.sym.Variable("%s_l%d_init_h" % (self.name, i))
                    self.last_states.append(
                        self.GRUState(
                            h = tmp_h
                        )
                    )
            else:
                self.forward_last_states = []
                self.backward_last_states = []
                for i in xrange(self.num_layers):
                    if self.states is not None:
                        slice_states = mx.sym.SliceChannel(
                            self.states[i], 
                            num_outputs = 2,
                            axis = 1,
                            name = "bi_init_states_slice_layer_%d" % i
                        )
                        tmp_forward_h = slice_states[0]
                        tmp_backward_h = slice_states[1]
                    else:
                        tmp_forward_h = mx.sym.Variable("%s_forward_l%d_init_h" % (self.name, i))
                        tmp_backward_h = mx.sym.Variable("%s_backward_l%d_init_h" % (self.name, i))
                    self.forward_last_states.append(
                        self.GRUState(
                            h = tmp_forward_h
                        )
                    )
                    self.backward_last_states.append(
                        self.GRUState(
                            h = tmp_backward_h
                        )
                    )              
        elif self.mode == 'lstm':
            if not self.bi_directional:
                self.last_states = []
                for i in range(self.num_layers):

                    if self.states is not None:
                        tmp_h = self.states[i]
                    else:
                        tmp_h = mx.sym.Variable("%s_l%d_init_h" % (self.name, i))
                    if self.cells is not None:
                        tmp_c = self.cells[i]
                    else:
                        tmp_c = mx.sym.Variable("%s_l%d_init_c" % (self.name, i))
                    self.last_states.append(
                        self.LSTMState(
                            c = tmp_c,
                            h = tmp_h
                        )
                    )
            else:
                self.forward_last_states = []
                self.backward_last_states = []
                for i in xrange(self.num_layers):
                    if self.states is not None:
                        slice_states = mx.sym.SliceChannel(
                            self.states[i], 
                            num_outputs = 2,
                            axis = 1,
                            name = "bi_init_states_slice_layer_%d" % i
                        )
                        tmp_forward_h = slice_states[0]
                        tmp_backward_h = slice_states[1]
                    else:
                        tmp_forward_h = mx.sym.Variable("%s_forward_l%d_init_h" % (self.name, i))
                        tmp_backward_h = mx.sym.Variable("%s_backward_l%d_init_h" % (self.name, i))
                    if self.cells is not None:
                        slice_cells = mx.sym.SliceChannel(
                            self.cells[i], 
                            num_outputs = 2,
                            axis = 1,
                            name = "bi_init_cells_slice_layer_%d" % i
                        )
                        tmp_forward_c = slice_cells[0]
                        tmp_backward_c = slice_cells[1]
                    else:
                        tmp_forward_c = mx.sym.Variable("%s_forward_l%d_init_c" % (self.name, i))
                        tmp_backward_c = mx.sym.Variable("%s_backward_l%d_init_c" % (self.name, i))
                    self.forward_last_states.append(
                        self.LSTMState(
                            c = tmp_forward_c,
                            h = tmp_forward_h
                        )
                    )
                    self.backward_last_states.append(
                        self.LSTMState(
                            c = tmp_backward_c,
                            h = tmp_backward_h
                        )
                    )  
        else:
            pass

    def lstm(self, num_hidden, indata, mask, prev_state, 
        param, seqidx, layeridx, dropout = 0.):
        """Basic  lstm cell function"""
        if dropout > 0.:
            indata = mx.sym.Dropout(data = indata, p = dropout)
        i2h = mx.sym.FullyConnected(
            data = indata,
            weight = param.i2h_weight,
            bias = param.i2h_bias,
            num_hidden = num_hidden * 4,                    
            name = "t%d_l%d_i2h" % (seqidx, layeridx)
        )
        h2h = mx.sym.FullyConnected(
            data = prev_state.h,
            weight = param.h2h_weight,
            bias = param.h2h_bias,
            num_hidden = num_hidden * 4,
            name = "t%d_l%d_h2h" % (seqidx, layeridx)
        )
        gates = i2h + h2h
        slice_gates = mx.sym.SliceChannel(
            data = gates, 
            num_outputs = 4,
            name = "t%d_l%d_h2h" % (seqidx, layeridx)
        )
        in_gate = mx.sym.Activation(slice_gates[0], act_type = "sigmoid")
        in_transform = mx.sym.Activation(slice_gates[1], act_type = "tanh")
        forget_gate = mx.sym.Activation(slice_gates[2], act_type = "sigmoid")
        out_gate = mx.sym.Activation(slice_gates[3], act_type = "sigmoid")
        next_c = (forget_gate * prev_state.c) + (in_gate * in_transform)
        next_h = out_gate * mx.sym.Activation(next_c, act_type = "tanh")
        if mask is not None:
            mask = mx.sym.Reshape(data = mask, shape = (-1, 1))
            next_c = mx.sym.broadcast_mul(next_c, mask, name = 'c_broadcast_mul')
            next_h = mx.sym.broadcast_mul(next_h, mask, name = 'h_broadcast_mul')
        
        return self.LSTMState(c = next_c, h = next_h)

    def gru(self, num_hidden, indata, mask, prev_state, 
        param, seqidx, layeridx, dropout = 0.):
        """Basic gru cell function"""
        if dropout > 0.:
            indata = mx.sym.Dropout(data = indata, p = dropout)
        i2h = mx.sym.FullyConnected(
            data = indata,
            weight = param.gates_i2h_weight,
            bias = param.gates_i2h_bias,
            num_hidden = num_hidden * 2,
            name = "t%d_l%d_gates_i2h"
        )
        h2h = mx.sym.FullyConnected(
            data = prev_state.h,
            weight = param.gates_h2h_weight,
            bias = param.gates_h2h_bias,
            num_hidden = num_hidden * 2,
            name = "t%d_l%d_gates_h2h"
        )
        gates = i2h + h2h
        slice_gates = mx.sym.SliceChannel(
            gates, 
            num_outputs = 2,
            name = "t%d_l%d_slice" % (seqidx, layeridx)
        )
        update_gate = mx.sym.Activation(slice_gates[0], act_type = "sigmoid")
        reset_gate = mx.sym.Activation(slice_gates[1], act_type = "sigmoid")
        htrans_i2h = mx.sym.FullyConnected(
            data = indata, 
            weight = param.trans_i2h_weight,
            bias = param.trans_i2h_bias,
            num_hidden = num_hidden,
            name = "t%d_l%d_trans_i2h" % (seqidx, layeridx)
        )
        h_after_reset = prev_state.h * reset_gate
        htrans_h2h = mx.sym.FullyConnected(
            data = h_after_reset,
            weight = param.trans_h2h_weight,
            bias = param.trans_h2h_bias,
            num_hidden = num_hidden,
            name = "t%d_l%d_trans_h2h" % (seqidx, layeridx)
        )
        h_trans = htrans_i2h + htrans_h2h
        h_trans_active = mx.sym.Activation(h_trans, act_type = "tanh")
        next_h = prev_state.h + update_gate * (h_trans_active - prev_state.h)
        if mask is not None:
            mask = mx.sym.Reshape(data = mask, shape = (-1, 1))
            next_h = mx.sym.broadcast_mul(next_h, mask, name = 'h_broadcast_mul')
        
        return self.GRUState(h = next_h)

    def get_variable_length_last_symbol(self, symbol_list, length_symbol):
        h_list = []
        for symbol in symbol_list:
            symbol = mx.sym.Reshape(data = symbol, shape = (-2,1))
            symbol = mx.sym.transpose(data  = symbol, axes = (2,0,1))
            h_list.append(symbol)
        h_concat = mx.sym.Concat(*h_list, dim = 0)

        if length_symbol is not None:
            last_h = mx.symbol.SequenceLast(
                data = h_concat,
                sequence_length = length_symbol,
                use_sequence_length = True,
                name = 'SequenceLast_last_h'
            )
        else:
            last_h = mx.symbol.SequenceLast(
                data = h_concat,
                use_sequence_length = False,
                name = 'SequenceLast_last_h'
            )
        return last_h             


    def lstm_unroll(self):
        """Explictly unroll rnn network"""

        ## maybe some problemin this symbol, attention
        wordvec = mx.sym.SliceChannel(
            data = self.data,
            num_outputs = self.seq_len,
            axis = 1,
            squeeze_axis = True,
            name = '%s_embed_slice_channel' % self.name
        )
        if self.mask is not None:
            maskvec = mx.sym.SliceChannel(
                data = self.mask, 
                num_outputs = self.seq_len, 
                axis = 1,
                squeeze_axis = True,
                name = '%s_mask_slice_channel' % self.name
            )
        # unrolled lstm
        last_layer_hidden_all = []
        hidden_all = [[] for _ in range(self.num_layers)]
        candidates_all = [[] for _ in range(self.num_layers)]
        for seqidx in xrange(self.seq_len):
            hidden = wordvec[seqidx]
            if self.mask is None:
                mask = None
            else:
                mask = maskvec[seqidx]
            ## stack lstm
            for i in xrange(self.num_layers):
                if i == 0:
                    dp_ratio = 0.
                else:
                    dp_ratio = self.dropout
                next_state = self.lstm(
                    num_hidden = self.num_hidden,
                    indata = hidden,
                    mask = mask,
                    prev_state = self.last_states[i],
                    param = self.param_cells[i],
                    seqidx = seqidx,
                    layeridx = i,
                    dropout = dp_ratio
                )
                hidden = next_state.h
                self.last_states[i] = next_state
                hidden_all[i].append(hidden)
                candidates_all[i].append(next_state.c)
            last_layer_hidden_all.append(hidden)

        outputs = {}
        last_time_hiddens = []
        last_time_cells = []
        for i in range(self.num_layers):
            last_h = self.get_variable_length_last_symbol(
                symbol_list = hidden_all[i], 
                length_symbol = self.real_seq_len
            )
            last_c = self.get_variable_length_last_symbol(
                symbol_list = candidates_all[i], 
                length_symbol = self.real_seq_len
            )
            last_time_hiddens.append(last_h)
            last_time_cells.append(last_c)
        outputs['last_layer'] = last_layer_hidden_all
        outputs['last_time'] = {'hidden': last_time_hiddens, 'cell': last_time_cells}
        return outputs

    def gru_unroll(self):
        """Explictly unroll rnn network"""

        ## maybe some problem in this symbol, attention
        wordvec = mx.sym.SliceChannel(
            data = self.data,
            num_outputs = self.seq_len,
            axis = 1,
            squeeze_axis = True,
            name = '%s_embed_slice_channel' % self.name
        )
        if self.mask is not None:
            maskvec = mx.sym.SliceChannel(
                data = self.mask, 
                num_outputs = self.seq_len, 
                axis = 1,
                squeeze_axis = True,
                name = '%s_mask_slice_channel' % self.name
            )
        # unrolled lstm
        last_layer_hidden_all = []
        hidden_all = [[] for _ in range(self.num_layers)]
        for seqidx in xrange(self.seq_len):
            hidden = wordvec[seqidx]
            if self.mask is None:
                mask = None
            else:
                mask = maskvec[seqidx]
            ## stack lstm
            for i in xrange(self.num_layers):
                if i == 0:
                    dp_ratio = 0.
                else:
                    dp_ratio = self.dropout
                next_state = self.gru(
                    num_hidden = self.num_hidden,
                    indata = hidden,
                    mask = mask,
                    prev_state = self.last_states[i],
                    param = self.param_cells[i],
                    seqidx = seqidx,
                    layeridx = i,
                    dropout = dp_ratio
                )
                hidden = next_state.h
                self.last_states[i] = next_state
                hidden_all[i].append(hidden)
            last_layer_hidden_all.append(hidden)
            #last_layer_hidden_all.append(update_gate)

        outputs = {}
        last_time_hidden_all = []
        for i in range(self.num_layers):
            last_h = self.get_variable_length_last_symbol(
                symbol_list = hidden_all[i], 
                length_symbol = self.real_seq_len
            )
            last_time_hidden_all.append(last_h)
        outputs['last_layer'] = last_layer_hidden_all
        outputs['last_time'] = {'hidden': last_time_hidden_all, 'cell': None}
        return outputs

    def bi_lstm_unroll(self):
        """Explictly unroll rnn network"""

        ## maybe some problemin this symbol, attention
        wordvec = mx.sym.SliceChannel(
            data = self.data,
            num_outputs = self.seq_len,
            axis = 1,
            squeeze_axis = True,
            name = '%s_embed_slice_channel' % self.name
        )
        if self.mask is not None:
            maskvec = mx.sym.SliceChannel(
                data = self.mask, 
                num_outputs = self.seq_len, 
                axis = 1,
                squeeze_axis = True,
                name = '%s_mask_slice_channel' % self.name
            )
        # unrolled lstm
        forward_last_layer_hidden_all = []
        forward_hidden_all = [[] for _ in range(self.num_layers)]
        forward_candidates_all = [[] for _ in range(self.num_layers)]
        
        for seqidx in xrange(self.seq_len):
            hidden = wordvec[seqidx]
            if self.mask is None:
                mask = None
            else:
                mask = maskvec[seqidx]
            ## stack lstm
            for i in xrange(self.num_layers):
                if i == 0:
                    dp_ratio = 0.
                else:
                    dp_ratio = self.dropout
                next_state = self.lstm(
                    num_hidden = self.num_hidden,
                    indata = hidden,
                    mask = mask,
                    prev_state = self.forward_last_states[i],
                    param = self.forward_param_cells[i],
                    seqidx = seqidx,
                    layeridx = i,
                    dropout = dp_ratio
                )
                hidden = next_state.h
                self.forward_last_states[i] = next_state
                forward_hidden_all[i].append(hidden)
                forward_candidates_all[i].append(next_state.c)
            forward_last_layer_hidden_all.append(hidden)

        backward_last_layer_hidden_all = []
        backward_hidden_all = [[] for _ in range(self.num_layers)]
        backward_candidates_all = [[] for _ in range(self.num_layers)]
        
        for seqidx in xrange(self.seq_len):
            k = self.seq_len - seqidx - 1
            hidden = wordvec[k]
            if self.mask is None:
                mask = None
            else:
                mask = maskvec[k]
            ## stack lstm
            for i in xrange(self.num_layers):
                if i == 0:
                    dp_ratio = 0.
                else:
                    dp_ratio = self.dropout
                next_state = self.lstm(
                    num_hidden = self.num_hidden,
                    indata = hidden,
                    mask = mask,
                    prev_state = self.backward_last_states[i],
                    param = self.backward_param_cells[i],
                    seqidx = k,
                    layeridx = i,
                    dropout = dp_ratio
                )
                hidden = next_state.h
                self.backward_last_states[i] = next_state
                backward_hidden_all.insert(0, hidden)
                backward_candidates_all.insert(0, next_state.c)
            backward_last_layer_hidden_all.insert(0, hidden)

        outputs = {}
        last_time_hiddens = []
        last_time_cells = []
        for i in range(self.num_layers):
            forward_last_h = self.get_variable_length_last_symbol(
                symbol_list = forward_hidden_all[i], 
                length_symbol = self.real_seq_len
            )
            forward_last_c = self.get_variable_length_last_symbol(
                symbol_list = forward_candidates_all[i], 
                length_symbol = self.real_seq_len
            )
            backward_last_h = backward_hidden_all[0]
            backward_last_c = backward_candidates_all[0]
            last_h = mx.sym.Concat(*[forward_last_h, backward_last_h], dim=1)
            last_c = mx.sym.Concat(*[forward_last_c, backward_last_c], dim=1)
            last_time_hiddens.append(last_h)
            last_time_cells.append(last_c)
        last_layer_hidden_all = []
        for i in xrange(self.seq_len):
            temp_symbol = mx.sym.Concat(*[forward_last_layer_hidden_all[i], backward_last_layer_hidden_all[i]], dim=1)
            last_layer_hidden_all.append(temp_symbol)
        outputs['last_layer'] = last_layer_hidden_all
        outputs['last_time'] = {'hidden' : last_time_hiddens, 'cell' : last_time_cells}
        return outputs     

    def bi_gru_unroll(self):
        """Explictly unroll rnn network"""

        ## maybe some problemin this symbol, attention
        wordvec = mx.sym.SliceChannel(
            data = self.data,
            num_outputs = self.seq_len,
            axis = 1,
            squeeze_axis = True,
            name = '%s_embed_slice_channel' % self.name
        )
        if self.mask is not None:
            maskvec = mx.sym.SliceChannel(
                data = self.mask, 
                num_outputs = self.seq_len, 
                axis = 1,
                squeeze_axis = True,
                name = '%s_mask_slice_channel' % self.name
            )
        # unrolled lstm
        forward_last_layer_hidden_all = []
        forward_hidden_all = [[] for _ in range(self.num_layers)]
        
        for seqidx in xrange(self.seq_len):
            hidden = wordvec[seqidx]
            if self.mask is None:
                mask = None
            else:
                mask = maskvec[seqidx]
            ## stack lstm
            for i in xrange(self.num_layers):
                if i == 0:
                    dp_ratio = 0.
                else:
                    dp_ratio = self.dropout
                next_state = self.gru(
                    num_hidden = self.num_hidden,
                    indata = hidden,
                    mask = mask,
                    prev_state = self.forward_last_states[i],
                    param = self.forward_param_cells[i],
                    seqidx = seqidx,
                    layeridx = i,
                    dropout = dp_ratio
                )
                hidden = next_state.h
                self.forward_last_states[i] = next_state
                forward_hidden_all[i].append(hidden)
            forward_last_layer_hidden_all.append(hidden)

        backward_last_layer_hidden_all = []
        backward_hidden_all = [[] for _ in range(self.num_layers)]
        
        for seqidx in xrange(self.seq_len):
            k = self.seq_len - seqidx - 1
            hidden = wordvec[k]
            if self.mask is None:
                mask = None
            else:
                mask = maskvec[k]
            ## stack lstm
            for i in xrange(self.num_layers):
                if i == 0:
                    dp_ratio = 0.
                else:
                    dp_ratio = self.dropout
                next_state = self.gru(
                    num_hidden = self.num_hidden,
                    indata = hidden,
                    mask = mask,
                    prev_state = self.backward_last_states[i],
                    param = self.backward_param_cells[i],
                    seqidx = k,
                    layeridx = i,
                    dropout = dp_ratio
                )
                hidden = next_state.h
                self.backward_last_states[i] = next_state
                backward_hidden_all.insert(0, hidden)
            backward_last_layer_hidden_all.insert(0, hidden)

        outputs = {}
        last_time_hidden_all = []
        for i in range(self.num_layers):
            forward_last_h = self.get_variable_length_last_symbol(
                symbol_list = forward_hidden_all[i], 
                length_symbol = self.real_seq_len
            )
            backward_last_h = backward_hidden_all[0]
            last_h = mx.sym.Concat(*[forward_last_h, backward_last_h], dim=1)
            last_time_hidden_all.append(last_h) 
        last_layer_hidden_all = []
        for i in xrange(self.seq_len):
            temp_symbol = mx.sym.Concat(*[forward_last_layer_hidden_all[i], backward_last_layer_hidden_all[i]], dim=1)
            last_layer_hidden_all.append(temp_symbol)
        outputs['last_layer'] = last_layer_hidden_all
        outputs['last_time'] = {'hidden' : last_time_hidden_all, 'cell' : None}
        return outputs

    def get_outputs(self):
        if self.mode == 'lstm' and not self.bi_directional:
            return self.lstm_unroll()
        elif self.mode == 'gru' and not self.bi_directional:
            return self.gru_unroll()
        elif self.mode == 'lstm' and self.bi_directional:
            return self.bi_lstm_unroll()
        elif self.mode == 'gru' and self.bi_directional:
            return self.bi_gru_unroll()
        else:
            raise Exception("Invalid parameters")